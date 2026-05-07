import json
import os
import pathlib

from openai import OpenAI

STRATEGY_FILE = pathlib.Path(__file__).parent / "STRATEGY.md"
OUTPUT_FILE = pathlib.Path(__file__).parent / "responses.json"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

RESPONSE_SCHEMA = """\
Each response object must follow this exact JSON schema:

{
  "persona": "<A|B|C|D|E|F>",
  "Q1":  "<single string — one of the allowed options>",
  "Q2":  "<single string>",
  "Q3":  "<single string>",
  "Q4":  "<single string>",
  "Q5":  "<single string>",
  "Q6":  "<single string>",
  "Q7":  ["<one or more strings from allowed options>"],
  "Q8":  "<single string>",
  "Q9":  "<single string>",
  "Q10": ["<one or more strings from allowed options>"],
  "Q11": "<single string>",
  "Q12": "<single string>",
  "Q13": "<single string>",
  "Q14": "<single string>",
  "Q15": "<single string>",
  "Q16": "<single string>",
  "Q17": "<single string>",
  "Q18": <integer 1–5>,
  "Q19": "<single string>",
  "Q20": <integer 1–5>
}

Rules:
- Q7 and Q10 MUST be JSON arrays (even when only one option is selected).
- Q18 and Q20 MUST be JSON integers (not strings).
- All option strings MUST exactly match the option text listed in §1 of the strategy document.
"""

PERSONAS = [
    ("A", "Świadomy Specjalista", 18),
    ("B", "Przeciętny Pracownik Biurowy", 28),
    ("C", "Pracownik z Małej Miejscowości", 20),
    ("D", "Senior z Doświadczeniem", 14),
    ("E", "Młody Entuzjasta", 12),
    ("F", "Pracownik Sektora Publicznego z Wiedzą KSC", 8),
]


def build_system_prompt(strategy_text: str) -> str:
    return (
        "You are a survey response generator.\n\n"
        "STRATEGY DOCUMENT (follow it strictly):\n"
        "========================================\n"
        + strategy_text
        + "\n========================================\n\n"
        "RESPONSE OBJECT SCHEMA:\n"
        + RESPONSE_SCHEMA
    )


def build_user_prompt(persona_code: str, persona_name: str, count: int) -> str:
    return (
        f"Generate exactly {count} survey responses for persona {persona_code} — {persona_name}.\n\n"
        "Requirements:\n"
        f"- Every response MUST have \"persona\": \"{persona_code}\".\n"
        "- Enforce every hard coherence rule from §5 on every single response — no exceptions.\n"
        "- Apply soft-rule probability weights from §5 realistically for this persona.\n"
        "- Vary answers within this persona's distributions; do not produce identical duplicates.\n\n"
        f"Return a single JSON object with the key \"responses\" containing an array of exactly {count} response objects."
    )


def main() -> None:
    strategy_text = STRATEGY_FILE.read_text(encoding="utf-8")
    system_prompt = build_system_prompt(strategy_text)

    client = OpenAI(api_key=OPENAI_API_KEY)

    all_responses = []
    for persona_code, persona_name, count in PERSONAS:
        print(f"Generating {count} responses for persona {persona_code} — {persona_name}...")
        user_prompt = build_user_prompt(persona_code, persona_name, count)
        completion = client.chat.completions.create(
            model="gpt-4.1",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        data = json.loads(completion.choices[0].message.content)
        responses = data["responses"]
        print(f"  Got {len(responses)} responses.")
        all_responses.extend(responses)

    OUTPUT_FILE.write_text(
        json.dumps(all_responses, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Written {len(all_responses)} responses to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
