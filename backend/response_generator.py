import json
import os
import pathlib
import sys
from typing import Callable

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

    @staticmethod
    def _resolve_persona_counts(personas: list, total: int) -> list:
        """Convert count_percent to absolute counts that sum exactly to total."""
        raw = [p["count_percent"] / 100 * total for p in personas]
        floored = [int(r) for r in raw]
        remainder = total - sum(floored)
        # Distribute remainder to personas with the largest fractional parts
        order = sorted(range(len(raw)), key=lambda i: raw[i] - floored[i], reverse=True)
        for i in range(remainder):
            floored[order[i]] += 1
        return [{**p, "count": floored[i]} for i, p in enumerate(personas)]

    def _format_strategy_json(
        self, strategy: dict, active_persona_code: str | None = None
    ) -> str:
        """Convert a JSON strategy dict into a rich text strategy document.

        When active_persona_code is set, omits research papers, aggregate
        distributions, and all other personas, cutting ~65% of input tokens
        while preserving everything the model needs to generate accurate responses.
        """
        questions_by_id = {q["id"]: q for q in self._config["questions"]}
        lines: list[str] = []

        # Research papers omitted per-persona: they add ~1,000 tokens but
        # don't help the model choose between specific answer options.
        if active_persona_code is None and strategy.get("research_basis"):
            lines.append("RESEARCH BASIS:")
            lines.append("=" * 15)
            for i, paper in enumerate(strategy["research_basis"], 1):
                lines.append(f'[{i}] "{paper["title"]}" — {paper["authors"]} ({paper.get("year", "")})')
                lines.append(f'    Source: {paper.get("source", "N/A")}')
                lines.append(f'    Abstract: {paper.get("abstract", "")}')
                if paper.get("key_findings"):
                    lines.append("    Key findings:")
                    for f in paper["key_findings"]:
                        lines.append(f"    \u2022 {f}")
                if paper.get("applicable_questions"):
                    lines.append(f'    Applicable to: {", ".join(paper["applicable_questions"])}')
                lines.append("")

        if strategy.get("topic_summary"):
            lines.append("TOPIC SUMMARY:")
            lines.append("=" * 14)
            lines.append(strategy["topic_summary"])
            lines.append("")

        # Aggregate distributions are redundant per-persona: the persona's own
        # weighted_answers already encode the correct target distribution.
        if active_persona_code is None:
            if strategy.get("demographic_distribution"):
                lines.append("AGGREGATE DEMOGRAPHIC DISTRIBUTIONS (Q1\u2013Q6, all respondents):")
                lines.append("=" * 62)
                for qid, dist in strategy["demographic_distribution"].items():
                    label = questions_by_id.get(qid, {}).get("label", qid)
                    dist_str = ", ".join(f"{opt}={pct}%" for opt, pct in dist.items())
                    lines.append(f"{qid} ({label}): {dist_str}")
                lines.append("")

            if strategy.get("question_distributions"):
                lines.append("AGGREGATE QUESTION DISTRIBUTIONS (among applicable respondents):")
                lines.append("=" * 62)
                for qid, dist in strategy["question_distributions"].items():
                    label = questions_by_id.get(qid, {}).get("label", qid)
                    dist_str = ", ".join(f"{opt}={pct}%" for opt, pct in dist.items())
                    lines.append(f"{qid} ({label[:70]}): {dist_str}")
                lines.append("")

        if strategy.get("personas"):
            personas_to_emit = (
                [p for p in strategy["personas"] if p["code"] == active_persona_code]
                if active_persona_code is not None
                else strategy["personas"]
            )
            lines.append("PERSONA:" if active_persona_code else "PERSONAS:")
            lines.append("=" * (8 if active_persona_code else 9))
            for persona in personas_to_emit:
                lines.append(
                    f'\n--- Persona {persona["code"]}: "{persona["name"]}" '
                    f'({persona["count_percent"]}% of responses) ---'
                )
                lines.append(f'Routing: Q6 = "{persona.get("routing", "N/A")}"')
                lines.append(f'Description: {persona.get("description", "")}')
                if persona.get("fixed_attributes"):
                    lines.append("\nFixed attributes (always this exact answer):")
                    for qid, val in persona["fixed_attributes"].items():
                        label = questions_by_id.get(qid, {}).get("label", qid)
                        lines.append(f'  {qid} ("{label[:60]}"): "{val}"')
                if persona.get("weighted_answers"):
                    lines.append(
                        "\nWeighted answer distributions "
                        "(integer weights per option, summing to 100 per question):"
                    )
                    for qid, dist in persona["weighted_answers"].items():
                        label = questions_by_id.get(qid, {}).get("label", qid)
                        dist_str = ", ".join(f"{opt}={pct}%" for opt, pct in dist.items())
                        lines.append(f'  {qid} ("{label[:60]}"): {dist_str}')
            lines.append("")

        if strategy.get("correlation_rules"):
            lines.append("CORRELATION RULES (enforce strictly on every response):")
            lines.append("=" * 53)
            for i, rule in enumerate(strategy["correlation_rules"], 1):
                lines.append(f'\n{i}. {rule.get("description", "")}')
                for qid, vals in rule.get("if", {}).items():
                    lines.append(f'   IF {qid} \u2208 {{"{chr(34) + chr(34).join(vals)}"}}' )
                for qid, dist in rule.get("then", {}).items():
                    dist_str = ", ".join(f"{opt}: {pct}%" for opt, pct in dist.items())
                    lines.append(f"   THEN {qid} weights \u2192 {{{dist_str}}}")
            lines.append("")

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
            "listed in the persona fixed_attributes and weighted_answers above."
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
            "- Enforce every rule from the CORRELATION RULES section "
            "on every single response — no exceptions.\n"
            "- Apply this persona's weighted_answers distributions; "
            "vary answers but respect the probability weights.\n"
            "- Vary answers within this persona's distributions; do not "
            "produce identical duplicates.\n\n"
            f'Return a single JSON object with the key "responses" containing '
            f"an array of exactly {count} response objects."
        )

    def generate(self, output_file: str | None = None, emit: Callable[[dict], None] | None = None) -> list:
        config = self._config

        strategy_path = pathlib.Path(config["strategy_file"])
        strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
        total = config.get("total_responses", 100)
        personas = self._resolve_persona_counts(strategy["personas"], total)

        model = "gpt-4.1"
        all_responses: list = []

        for persona in personas:
            code, name, count = persona["code"], persona["name"], persona["count"]
            # Build a focused system prompt containing only this persona's data.
            strategy_text = self._format_strategy_json(strategy, active_persona_code=code)
            system_prompt = self._build_system_prompt(strategy_text)
            msg = (
                f"Generating {count} responses for persona {code} — {name} "
                f"(~{len(system_prompt) // 4} input tokens in system prompt)..."
            )
            print(msg)
            if emit:
                emit({"type": "message", "text": f"Generating {count} responses for persona {code} — {name}"})
            completion = self._client.chat.completions.create(
                model=model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": self._build_user_prompt(code, name, count)},
                ],
            )
            batch = json.loads(completion.choices[0].message.content)["responses"]
            msg2 = f"  Got {len(batch)} responses."
            print(msg2)
            if emit:
                emit({"type": "message", "text": msg2})
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
    config_path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "data/form_config_1.json")
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    config = json.loads(config_path.read_text(encoding="utf-8"))
    ResponseGenerator(config).generate(output_file=output_file)


if __name__ == "__main__":
    main()
