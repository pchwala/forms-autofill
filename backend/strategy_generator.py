"""strategy_generator.py — 3-step GPT-5 pipeline that generates a JSON strategy file
for survey response generation.

Steps:
  1. Web search  → data/research_basis_N.json
  2. Analysis    → data/research_analysis_N.json
  3. Compile     → data/strategy_N.json

Usage:
    python strategy_generator.py data/form_config_1.json
    python strategy_generator.py data/form_config_1.json --step 2   # resume from step 2
    python strategy_generator.py data/form_config_1.json --output data/my_strategy.json
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
from typing import Callable

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_base_name(config_path: pathlib.Path) -> str:
    """Extract the base name from a {base_name}_form_config.json path."""
    name = config_path.name
    if not name.endswith("_form_config.json"):
        raise ValueError(f"Unexpected config filename: {name!r}; expected *_form_config.json")
    return name[: -len("_form_config.json")]


def _build_question_summary(questions: list, routing: list) -> str:
    """Compact multi-line description of every question with all valid option strings."""
    skippable: set[str] = set()
    for rule in routing:
        for cond in rule.get("conditions", []):
            skippable.update(cond.get("skipped_question_ids", []))

    lines: list[str] = []
    for q in questions:
        opts = " / ".join(q.get("options", [])) or "(open-ended)"
        note = (
            "  [may be null — routing skips this for some respondents]"
            if q["id"] in skippable
            else ""
        )
        lines.append(f"  {q['id']}: {q['label']}")
        lines.append(f"    Type: {q['type']}, Options: {opts}{note}")
    return "\n".join(lines)


def _parse_json_from_text(text: str) -> dict:
    """Robustly extract a JSON object from model output, stripping code fences."""
    text = text.strip()
    text = re.sub(r"^```[a-z]*\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n?```\s*$", "", text, flags=re.MULTILINE)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise


# ---------------------------------------------------------------------------
# Core class
# ---------------------------------------------------------------------------


class StrategyGenerator:
    def __init__(
        self,
        config: dict,
        config_path: pathlib.Path,
        data_dir: pathlib.Path,
        desire_prompt: str | None = None,
    ) -> None:
        self._config = config
        self._base_name = _extract_base_name(config_path)
        self._data_dir = data_dir
        self._desire_prompt = (desire_prompt or "").strip() or None
        self._client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self._model = "gpt-4.1"

    def _directive_block(self) -> str:
        """High-priority user directive that outranks the research-based distributions.

        Returned as a prompt prefix (empty string when no desire prompt was given).
        """
        if not self._desire_prompt:
            return ""
        return (
            "USER DIRECTIVE — HIGHEST PRIORITY. The person running this survey has "
            "explicitly requested the following desired outcome. Whenever it conflicts "
            "with the research-based statistics, the directive WINS: skew the "
            "distributions, persona mix, and weighted answers so the aggregate result "
            "matches this request as closely as the question options allow.\n"
            f'DIRECTIVE: "{self._desire_prompt}"\n\n'
        )

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def _research_basis_path(self) -> pathlib.Path:
        return self._data_dir / f"{self._base_name}_research_basis.json"

    def _research_analysis_path(self) -> pathlib.Path:
        return self._data_dir / f"{self._base_name}_research_analysis.json"

    def _strategy_path(self, output: str | None) -> pathlib.Path:
        if output:
            return pathlib.Path(output)
        return self._data_dir / f"{self._base_name}_strategy.json"

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(
        self,
        start_step: int = 1,
        output: str | None = None,
        emit: Callable[[dict], None] | None = None,
    ) -> pathlib.Path:
        # ── Step 1: Web search ──────────────────────────────────────────
        if start_step <= 1:
            msg = "Krok 1/3 — Wyszukiwanie artykułów badawczych"
            print(msg)
            if emit:
                emit({"type": "message", "text": msg})
            research_basis = self._step1_web_search()
            rb_path = self._research_basis_path()
            rb_path.write_text(
                json.dumps(research_basis, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            n = len(research_basis.get("research_basis", []))
            msg2 = f"  Znaleziono {n} artykuł(ów)."
            print(msg2 + f" Saved → {rb_path}")
            if emit:
                emit({"type": "message", "text": msg2})
        else:
            rb_path = self._research_basis_path()
            research_basis = json.loads(rb_path.read_text(encoding="utf-8"))
            n = len(research_basis.get("research_basis", []))
            msg = f"Krok 1/3 — Pominięto (załadowano {n} artykuł(ów) z {rb_path})"
            print(msg)
            if emit:
                emit({"type": "message", "text": msg})

        # ── Step 2: Analysis ────────────────────────────────────────────
        if start_step <= 2:
            msg = "Krok 2/3 — Analizowanie artykułów, budowanie rozkładów i archetypów person"
            print(msg)
            if emit:
                emit({"type": "message", "text": msg})
            research_analysis = self._step2_analyze(research_basis)
            ra_path = self._research_analysis_path()
            ra_path.write_text(
                json.dumps(research_analysis, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            np_ = len(research_analysis.get("suggested_personas", []))
            msg2 = f"  Utworzono {np_} archetyp(ów) person."
            print(msg2 + f" Saved → {ra_path}")
            if emit:
                emit({"type": "message", "text": msg2})
        else:
            ra_path = self._research_analysis_path()
            research_analysis = json.loads(ra_path.read_text(encoding="utf-8"))
            np_ = len(research_analysis.get("suggested_personas", []))
            msg = f"Krok 2/3 — Pominięto (załadowano {np_} archetyp(ów) z {ra_path})"
            print(msg)
            if emit:
                emit({"type": "message", "text": msg})

        # ── Step 3: Compile final strategy ──────────────────────────────
        msg = "Krok 3/3 — Kompilowanie person i finalnej strategii"
        print(msg)
        if emit:
            emit({"type": "message", "text": msg})
        strategy = self._step3_compile(research_basis, research_analysis)
        dest = self._strategy_path(output)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            json.dumps(strategy, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        np_ = len(strategy.get("personas", []))
        msg2 = f"  Skompilowano {np_} person."
        print(msg2 + f" Saved → {dest}")
        print(
            f'\nDone! Set "strategy_file": "{dest}" in your form_config, '
            f'and optionally add "total_responses": 100.'
        )
        if emit:
            emit({"type": "message", "text": msg2})
        return dest

    # ------------------------------------------------------------------
    # Step 1 — Web search
    # ------------------------------------------------------------------

    def _step1_web_search(self) -> dict:
        config = self._config
        form_title = config.get("form_title", "survey")
        labels = [q["label"] for q in config["questions"]]
        topic_sample = "; ".join(labels[:8])

        prompt = f"""You are a research assistant helping build a realistic synthetic dataset \
for a survey.

Survey title: "{form_title}"
Sample survey questions: {topic_sample}

Use the web search tool to find 4 to 5 peer-reviewed academic papers or large-scale surveys \
that provide empirical quantitative data (percentages, statistics) relevant to the topics above.

Requirements:
- Only use real, verifiable papers with real authors and real publication details.
- Prefer studies from Europe, especially Poland or Central/Eastern Europe, when available.
- Each paper must include at least one concrete statistic or percentage finding.
- Search in English.
- Do NOT fabricate citations.

Return ONLY a JSON object matching this schema exactly (no markdown, no explanation):
{{
  "research_basis": [
    {{
      "title": "Full paper title",
      "authors": "Author A, Author B",
      "year": 2020,
      "source": "Journal name, DOI, or URL",
      "abstract": "2-3 sentence summary of the study and its methodology",
      "key_findings": [
        "Specific finding 1 with exact percentage or statistic",
        "Specific finding 2 with exact percentage or statistic"
      ],
      "applicable_questions": ["Q9", "Q14"]
    }}
  ]
}}

LANGUAGE: Write all descriptive text values (abstract, key_findings text) in Polish (język polski). JSON field names and question IDs MUST remain exactly as given."""

        response = self._client.responses.create(
            model=self._model,
            tools=[{"type": "web_search_preview"}],
            input=[{"role": "user", "content": prompt}],
        )
        return _parse_json_from_text(response.output_text)

    # ------------------------------------------------------------------
    # Step 2 — Analysis
    # ------------------------------------------------------------------

    def _step2_analyze(self, research_basis: dict) -> dict:
        config = self._config
        q_summary = _build_question_summary(config["questions"], config.get("routing", []))
        routing_json = json.dumps(config.get("routing", []), ensure_ascii=False, indent=2)

        prompt = f"""You are a survey methodology expert. Using the research papers and the \
survey structure below, create a statistically grounded distribution plan for generating \
realistic synthetic responses.

RESEARCH PAPERS:
{json.dumps(research_basis, ensure_ascii=False, indent=2)}

SURVEY QUESTIONS (type and all valid option strings):
{q_summary}

ROUTING RULES:
{routing_json}

Instructions:
1. For every question assign a realistic percentage distribution over its options, \
grounded in the research.
   - Questions Q1–Q6 cover ALL 100% of respondents.
   - Questions marked "[may be null — routing skips this]" cover only the respondents who see them.
   - Every distribution MUST sum to exactly 100.
2. Propose 3 to 5 distinct persona archetypes whose weighted mix reproduces these distributions.
   - All persona count_percent values MUST sum to exactly 100.
3. Identify 3 to 7 important correlations between questions \
(e.g., higher education → higher awareness on Q13).

Return ONLY a JSON object with this schema (no markdown, no explanation):
{{
  "topic_summary": "2-3 sentences describing what the research tells us about this population",
  "demographic_distribution": {{
    "Q1": {{"<exact option text>": <integer percent>, ...}},
    "Q2": {{}},
    "Q3": {{}},
    "Q4": {{}},
    "Q5": {{}},
    "Q6": {{}}
  }},
  "question_distributions": {{
    "Q7": {{"<exact option text>": <integer percent>, ...}},
    "Q8": {{}},
    "Q9": {{}},
    "Q10": {{}},
    "Q11": {{}},
    "Q12": {{}},
    "Q13": {{}},
    "Q14": {{}},
    "Q15": {{}},
    "Q16": {{}},
    "Q17": {{}},
    "Q18": {{}},
    "Q19": {{}},
    "Q20": {{}},
    "Q21": {{}},
    "Q22": {{}},
    "Q23": {{}},
    "Q24": {{}},
    "Q25": {{}},
    "Q26": {{}},
    "Q27": {{}},
    "Q28": {{}}
  }},
  "suggested_personas": [
    {{
      "name": "Descriptive persona name",
      "description": "2-3 sentence description of this archetype's profile and behaviors",
      "count_percent": <integer>,
      "archetype_traits": ["trait 1", "trait 2", "trait 3"],
      "routing_answer": "<exact Q6 option text>"
    }}
  ],
  "correlation_rules": [
    {{
      "description": "Plain English description",
      "if": {{"<question_id>": ["<option_a>", "<option_b>"]}},
      "then": {{"<question_id>": {{"<option>": <integer percent>, ...}}}}
    }}
  ]
}}

LANGUAGE: Write all descriptive text values (topic_summary, persona name, persona description, correlation rule description) in Polish (język polski). JSON field names, question IDs, and option strings that appear verbatim in the survey questions MUST remain exactly as given."""

        completion = self._client.chat.completions.create(
            model=self._model,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are a survey methodology expert. Return only valid JSON.",
                },
                {"role": "user", "content": self._directive_block() + prompt},
            ],
        )
        return json.loads(completion.choices[0].message.content)

    # ------------------------------------------------------------------
    # Step 3 — Compile final strategy
    # ------------------------------------------------------------------

    def _step3_compile(self, research_basis: dict, research_analysis: dict) -> dict:
        config = self._config
        q_summary = _build_question_summary(config["questions"], config.get("routing", []))

        prompt = f"""You are a survey methodology expert. Using the research basis and \
analysis below, compile a complete JSON strategy for generating realistic synthetic survey \
responses.

RESEARCH BASIS:
{json.dumps(research_basis, ensure_ascii=False, indent=2)}

ANALYSIS (topic summary, distributions, persona archetypes, correlations):
{json.dumps(research_analysis, ensure_ascii=False, indent=2)}

SURVEY QUESTIONS (type and all valid option strings):
{q_summary}

Instructions:
1. Flesh out each suggested persona into a complete persona entry with code (A, B, C, …), \
name, count_percent, description, and routing (exact Q6 answer text).
2. For each persona assign:
   - fixed_attributes: questions where this persona ALWAYS gives the same single answer.
     Typically Q1 (gender), Q2 (city size), Q4 (education) if stable for this archetype.
     Also include Q6 here (the routing question).
   - weighted_answers: every other applicable non-fixed question, with exact option \
strings as keys and integer weights that sum to exactly 100 per question.
3. Questions SKIPPED by routing for a persona MUST NOT appear in fixed_attributes or \
weighted_answers (they will be submitted as null).
4. All persona count_percent values MUST sum to exactly 100.
5. When aggregated by count_percent, persona distributions should approximate the \
demographic_distribution and question_distributions from the analysis.

Return ONLY a JSON object with this schema (no markdown, no explanation):
{{
  "research_basis": [ ...copy from research basis... ],
  "topic_summary": "...",
  "demographic_distribution": {{ ...copy from analysis... }},
  "question_distributions": {{ ...copy from analysis... }},
  "personas": [
    {{
      "code": "A",
      "name": "persona name",
      "count_percent": <integer>,
      "description": "description",
      "routing": "<exact Q6 option text>",
      "fixed_attributes": {{
        "<question_id>": "<exact option text>"
      }},
      "weighted_answers": {{
        "<question_id>": {{
          "<exact option text>": <integer weight 0-100>,
          ...all options for this question, weights sum to 100...
        }}
      }}
    }}
  ],
  "correlation_rules": [ ...copy from analysis... ]
}}

LANGUAGE: Write all descriptive text values (topic_summary, persona name, persona description, correlation rule description) in Polish (język polski). JSON field names, question IDs, and option strings that appear verbatim in the survey questions MUST remain exactly as given."""

        completion = self._client.chat.completions.create(
            model=self._model,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are a survey methodology expert. Return only valid JSON.",
                },
                {"role": "user", "content": self._directive_block() + prompt},
            ],
        )
        result = json.loads(completion.choices[0].message.content)
        # Always source routing_rules directly from the config for accuracy.
        result["routing_rules"] = config.get("routing", [])
        return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run(
    config_path: str | pathlib.Path,
    start_step: int = 1,
    output: str | None = None,
    emit: Callable[[dict], None] | None = None,
    desire_prompt: str | None = None,
) -> pathlib.Path:
    """Run the strategy generation pipeline and return the path to the strategy JSON.

    Args:
        config_path:   Path to form_config_N.json.
        start_step:    1 = full run, 2 = skip web search, 3 = skip web search + analysis.
        output:        Custom output path (default: data/strategy_N.json).
        emit:          Optional SSE emit callback for streaming progress events.
        desire_prompt: Optional high-priority user directive that skews the generated
                       distributions/personas toward a requested outcome.
    """
    config_path = pathlib.Path(config_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    data_dir = pathlib.Path("data")
    data_dir.mkdir(exist_ok=True)
    return StrategyGenerator(config, config_path, data_dir, desire_prompt=desire_prompt).run(
        start_step=start_step,
        output=output,
        emit=emit,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a JSON strategy file for a Google Form config "
            "using a 3-step GPT pipeline."
        )
    )
    parser.add_argument("config", help="Path to form_config_N.json")
    parser.add_argument(
        "--step",
        type=int,
        choices=[1, 2, 3],
        default=1,
        metavar="{1,2,3}",
        help=(
            "Resume from this step: "
            "1=full run (default), "
            "2=skip web search (needs data/research_basis_N.json), "
            "3=skip web search + analysis (needs data/research_analysis_N.json)"
        ),
    )
    parser.add_argument(
        "--output",
        help="Output path for the strategy JSON (default: data/strategy_N.json)",
    )
    args = parser.parse_args()

    config_path = pathlib.Path(args.config)
    if not config_path.exists():
        print(f"Error: config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    config = json.loads(config_path.read_text(encoding="utf-8"))
    data_dir = pathlib.Path("data")
    data_dir.mkdir(exist_ok=True)

    StrategyGenerator(config, config_path, data_dir).run(
        start_step=args.step,
        output=args.output,
    )


if __name__ == "__main__":
    run(config_path="data/form_config_1.json")
