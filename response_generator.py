import json
import os
import pathlib
import sys

from openai import OpenAI


class ResponseGenerator:
    """Generates persona-driven survey responses via the OpenAI API.

    All form-specific data (personas, question types, model, paths) is read
    from a config dict, typically loaded from a per-form JSON file.
    """

    def __init__(self, config: dict) -> None:
        self._config = config
        self._client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def _get_conditional_question_ids(self) -> set[str]:
        """Return all question IDs that may be skipped due to routing conditions."""
        skipped: set[str] = set()
        for rule in self._config.get("routing", []):
            for cond in rule["conditions"]:
                skipped.update(cond.get("skipped_question_ids", []))
        return skipped

    def _build_routing_text(self) -> str:
        """Generate a human-readable block describing all form routing rules."""
        routing = self._config.get("routing", [])
        if not routing:
            return ""

        lines = [
            "FORM ROUTING RULES (CRITICAL — violations make responses impossible to submit):",
            "Whenever a routing rule applies, set the skipped questions to JSON null.",
        ]
        for rule in routing:
            lines.append(f"\nQuestion {rule['question_id']} — \"{rule['label']}\":")
            for cond in rule["conditions"]:
                val = cond["value"]
                go_to = cond["go_to"]
                skipped = cond.get("skipped_question_ids", [])

                if go_to == "submit":
                    lines.append(f"  \u2022 Answer \"{val}\" \u2192 FORM ENDS IMMEDIATELY.")
                    if skipped:
                        lines.append(
                            f"    The following questions MUST be null: {skipped}"
                        )
                elif go_to is None or go_to == "next_page":
                    lines.append(
                        f"  \u2022 Answer \"{val}\" \u2192 normal flow "
                        "(all subsequent questions apply)."
                    )
                else:
                    lines.append(f"  \u2022 Answer \"{val}\" \u2192 jump to {go_to}.")
                    if skipped:
                        lines.append(
                            f"    The following questions are SKIPPED "
                            f"and MUST be null: {skipped}"
                        )
        return "\n".join(lines)

    def _build_response_schema(self) -> str:
        questions = self._config["questions"]
        conditional_ids = self._get_conditional_question_ids()
        lines = [
            "Each response object must follow this exact JSON schema:",
            "",
            "{",
            '  "persona": "<code>",',
        ]
        for q in questions:
            qid = q["id"]
            nullable = qid in conditional_ids
            suffix = "  // null when routing skips this question" if nullable else ""
            if q["type"] == "checkbox":
                lines.append(
                    f'  "{qid}": ["<one or more strings from allowed options>"] or null,{suffix}'
                    if nullable
                    else f'  "{qid}": ["<one or more strings from allowed options>"],'
                )
            elif q["type"] == "scale":
                lines.append(
                    f'  "{qid}": <integer> or null,{suffix}'
                    if nullable
                    else f'  "{qid}": <integer>,'
                )
            else:
                lines.append(
                    f'  "{qid}": "<single string — one of the allowed options>" or null,{suffix}'
                    if nullable
                    else f'  "{qid}": "<single string — one of the allowed options>",'
                )
        lines[-1] = lines[-1].rstrip(",")  # remove trailing comma on last field
        lines.append("}")

        checkbox_ids = [q["id"] for q in questions if q["type"] == "checkbox"]
        scale_ids = [q["id"] for q in questions if q["type"] == "scale"]

        rules = ["", "Rules:"]
        if checkbox_ids:
            rules.append(
                f"- {', '.join(checkbox_ids)} MUST be JSON arrays "
                "(even when only one option is selected)."
            )
        if scale_ids:
            rules.append(
                f"- {', '.join(scale_ids)} MUST be JSON integers (not strings)."
            )
        rules.append(
            "- All option strings MUST exactly match the option text "
            "listed in §1 of the strategy document."
        )
        if conditional_ids:
            rules.append(
                "- Questions marked 'or null' MUST be JSON null (not absent, not empty string) "
                "when a routing rule skips them."
            )
        return "\n".join(lines + rules)

    def _build_system_prompt(self, strategy_text: str) -> str:
        routing_text = self._build_routing_text()
        return (
            "You are a survey response generator.\n\n"
            "STRATEGY DOCUMENT (follow it strictly):\n"
            "========================================\n"
            + strategy_text
            + "\n========================================\n\n"
            + (routing_text + "\n\n" if routing_text else "")
            + "RESPONSE OBJECT SCHEMA:\n"
            + self._build_response_schema()
        )

    def _build_user_prompt(self, persona_code: str, persona_name: str, count: int) -> str:
        return (
            f"Generate exactly {count} survey responses for persona "
            f"{persona_code} — {persona_name}.\n\n"
            "Requirements:\n"
            f'- Every response MUST have "persona": "{persona_code}".\n'
            "- Enforce every hard coherence rule from §5 on every single "
            "response — no exceptions.\n"
            "- Apply soft-rule probability weights from §5 realistically "
            "for this persona.\n"
            "- Vary answers within this persona's distributions; do not "
            "produce identical duplicates.\n\n"
            f'Return a single JSON object with the key "responses" containing '
            f"an array of exactly {count} response objects."
        )

    def generate(self, output_file: str | None = None) -> list:
        config = self._config

        # Resolve strategy_file relative to wherever the config file lives.
        strategy_path = pathlib.Path(config["strategy_file"])
        strategy_text = strategy_path.read_text(encoding="utf-8")
        system_prompt = self._build_system_prompt(strategy_text)

        model = config.get("model", "gpt-4.1")
        all_responses: list = []

        for persona in config["personas"]:
            code, name, count = persona["code"], persona["name"], persona["count"]
            print(f"Generating {count} responses for persona {code} — {name}...")
            completion = self._client.chat.completions.create(
                model=model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": self._build_user_prompt(code, name, count)},
                ],
            )
            batch = json.loads(completion.choices[0].message.content)["responses"]
            print(f"  Got {len(batch)} responses.")
            all_responses.extend(batch)

        if output_file is not None:
            dest = pathlib.Path(output_file)
        else:
            base = pathlib.Path(config.get("output_file", "data/responses.json"))
            dest = _next_numbered_path(base)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            json.dumps(all_responses, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Written {len(all_responses)} responses to {dest}")
        return all_responses


def _next_numbered_path(base: pathlib.Path) -> pathlib.Path:
    """Return the first non-existing path of the form <stem>_N<suffix>."""
    n = 1
    while True:
        candidate = base.parent / f"{base.stem}_{n}{base.suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def main() -> None:
    config_path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "data/form_config.json")
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    config = json.loads(config_path.read_text(encoding="utf-8"))
    ResponseGenerator(config).generate(output_file=output_file)


if __name__ == "__main__":
    main()
