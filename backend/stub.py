"""stub.py — Stub switch for AI model calls.

When AI_SWITCH_STUB=true in the environment, every AI model call is replaced
with a 10-second delay plus minimal canned data so the full pipeline can be
tested without consuming API tokens.

Usage:
    import backend.stub as stub

    if stub.is_stub():
        stub.stub_sleep()
        return stub.make_stub_research_basis()
"""

from __future__ import annotations

import os
import time

from dotenv import load_dotenv

load_dotenv()


def is_stub() -> bool:
    """Return True when AI_SWITCH_STUB is set to 'true' in the environment."""
    return os.getenv("AI_SWITCH_STUB", "false").lower() == "true"


def stub_sleep() -> None:
    """Sleep 10 seconds to simulate model latency."""
    time.sleep(10)


# ---------------------------------------------------------------------------
# Stub data factories
# ---------------------------------------------------------------------------


def make_stub_research_basis() -> dict:
    return {
        "research_basis": [
            {
                "title": "[STUB] Placeholder Study",
                "authors": "Stub Author",
                "year": 2024,
                "source": "N/A (stub mode — no real API call was made)",
                "abstract": "This is a stub research entry used for testing the pipeline.",
                "key_findings": [
                    "50% of respondents preferred the first available option.",
                    "Stub data is evenly distributed across all answer choices.",
                ],
                "applicable_questions": [],
            }
        ]
    }


def make_stub_analysis(config: dict) -> dict:
    """Build a minimal research analysis dict from the form config."""
    questions = config["questions"]
    routing = config.get("routing", [])

    skippable: set[str] = set()
    for rule in routing:
        for cond in rule.get("conditions", []):
            skippable.update(cond.get("skipped_question_ids", []))

    def _even_dist(options: list) -> dict:
        if not options:
            return {}
        n = len(options)
        base = 100 // n
        dist = {opt: base for opt in options}
        dist[options[0]] += 100 - base * n  # remainder to first option
        return dist

    demographic_ids = {f"Q{i}" for i in range(1, 7)}
    demographic_distribution: dict = {}
    question_distributions: dict = {}

    for q in questions:
        opts = q.get("options", [])
        dist = _even_dist(opts) if opts else {"(open-ended)": 100}
        if q["id"] in demographic_ids:
            demographic_distribution[q["id"]] = dist
        elif q["id"] not in skippable:
            question_distributions[q["id"]] = dist

    q6_first = _q6_first_option(config)
    return {
        "topic_summary": "[STUB] Placeholder topic summary for pipeline testing.",
        "demographic_distribution": demographic_distribution,
        "question_distributions": question_distributions,
        "suggested_personas": [
            {
                "name": "Stub Persona",
                "description": "A single stub persona covering all respondents.",
                "count_percent": 100,
                "archetype_traits": ["stub"],
                "routing_answer": q6_first,
            }
        ],
        "correlation_rules": [],
    }


def make_stub_strategy(config: dict, research_basis: dict, research_analysis: dict) -> dict:
    """Build a minimal strategy dict from the form config and stub intermediate data."""
    questions = config["questions"]
    routing = config.get("routing", [])

    # Determine which questions are potentially skippable.
    skippable: set[str] = set()
    for rule in routing:
        for cond in rule.get("conditions", []):
            skippable.update(cond.get("skipped_question_ids", []))

    fixed_ids = {"Q1", "Q2", "Q4", "Q6"}
    fixed_attributes: dict = {}
    weighted_answers: dict = {}

    for q in questions:
        qid = q["id"]
        if qid in skippable:
            # Skipped questions are omitted entirely (submitted as null).
            continue
        opts = q.get("options", [])
        if qid in fixed_ids:
            fixed_attributes[qid] = opts[0] if opts else "N/A"
        else:
            if opts:
                n = len(opts)
                base = 100 // n
                dist = {opt: base for opt in opts}
                dist[opts[0]] += 100 - base * n
                weighted_answers[qid] = dist

    return {
        "research_basis": research_basis.get("research_basis", []),
        "topic_summary": research_analysis.get("topic_summary", "[STUB]"),
        "demographic_distribution": research_analysis.get("demographic_distribution", {}),
        "question_distributions": research_analysis.get("question_distributions", {}),
        "personas": [
            {
                "code": "A",
                "name": "Stub Persona",
                "count_percent": 100,
                "description": "A single stub persona covering all respondents.",
                "routing": _q6_first_option(config),
                "fixed_attributes": fixed_attributes,
                "weighted_answers": weighted_answers,
            }
        ],
        "correlation_rules": [],
        "routing_rules": routing,
    }


def make_stub_responses(config: dict, personas: list) -> list:
    """Generate minimal valid responses from the form config without calling AI.

    Each persona entry must include a 'count' key (resolved absolute count).
    """
    questions = config["questions"]
    routing = config.get("routing", [])

    skippable: set[str] = set()
    for rule in routing:
        for cond in rule.get("conditions", []):
            skippable.update(cond.get("skipped_question_ids", []))

    all_responses: list = []
    for persona in personas:
        fixed = persona.get("fixed_attributes", {})
        for _ in range(persona["count"]):
            response: dict = {"persona": persona["code"]}
            for q in questions:
                qid = q["id"]
                if qid in skippable:
                    response[qid] = None
                elif qid in fixed:
                    response[qid] = fixed[qid]
                else:
                    opts = q.get("options", [])
                    if q["type"] == "checkbox":
                        response[qid] = [opts[0]] if opts else []
                    elif q["type"] == "scale":
                        response[qid] = int(opts[0]) if opts else 1
                    else:
                        response[qid] = opts[0] if opts else ""
            all_responses.append(response)
    return all_responses


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _q6_first_option(config: dict) -> str:
    for q in config["questions"]:
        if q["id"] == "Q6":
            opts = q.get("options", [])
            return opts[0] if opts else "N/A"
    return "N/A"
