"""preview.py — Compute the free, pre-payment preview from a generated strategy.

The strategy JSON already encodes target distributions (each persona's
``fixed_attributes``/``weighted_answers`` weighted by ``count_percent``), so we can
show the user the *predicted* answer distribution for the first few questions
without making any (paid) response-generation call. Actual generation/submission
happens only after payment.
"""

from __future__ import annotations

import copy

# Question types that have discrete options worth charting in the preview.
OPTION_TYPES = {"radio", "checkbox", "dropdown", "scale", "grid_row"}

PREVIEW_QUESTION_LIMIT = 10


def select_preview_questions(config: dict, limit: int = PREVIEW_QUESTION_LIMIT) -> list[dict]:
    """Return the first `limit` option-based questions in form order (free-text skipped)."""
    picked: list[dict] = []
    for q in config.get("questions", []):
        if q.get("type") in OPTION_TYPES and q.get("options"):
            picked.append(q)
            if len(picked) >= limit:
                break
    return picked


def persona_answer_weights(persona: dict, qid: str) -> dict[str, float] | None:
    """Per-option weights this persona contributes for `qid`.

    Returns ``{option: 100}`` for a fixed attribute, the persona's
    ``weighted_answers`` dict otherwise, or ``None`` when the persona never answers
    this question (routing-skipped or absent from the strategy).
    """
    fixed = persona.get("fixed_attributes", {})
    if qid in fixed:
        return {fixed[qid]: 100.0}
    weighted = persona.get("weighted_answers", {})
    if qid in weighted:
        return {opt: float(w) for opt, w in weighted[qid].items()}
    return None


def aggregate_distributions(
    personas: list[dict],
    selected_codes: list[str],
    questions: list[dict],
) -> list[dict]:
    """Aggregate per-persona option weights into overall distributions.

    `personas` are summaries with at least ``code`` and ``count_percent``.
    `questions` carry a ``per_persona`` map ``{code: {option: weight} | None}``.
    Selected personas are renormalized to 100%; personas that skip a question
    (``None``) are excluded from that question's base and reported as a skipped %.
    This mirrors the client-side recompute done when checkboxes are toggled.
    """
    code_to_pct = {p["code"]: p["count_percent"] for p in personas}
    selected = [c for c in selected_codes if c in code_to_pct]
    selected_total = sum(code_to_pct[c] for c in selected) or 1

    result: list[dict] = []
    for q in questions:
        per_persona: dict = q["per_persona"]
        options: list[str] = q.get("options", [])
        contributing = [c for c in selected if per_persona.get(c) is not None]
        contributing_total = sum(code_to_pct[c] for c in contributing)

        opt_pct: dict[str, float] = {opt: 0.0 for opt in options}
        if contributing_total > 0:
            for c in contributing:
                share = code_to_pct[c] / contributing_total
                for opt, w in per_persona[c].items():
                    opt_pct[opt] = opt_pct.get(opt, 0.0) + share * w

        skipped_percent = round((selected_total - contributing_total) / selected_total * 100)
        result.append(
            {
                "id": q["id"],
                "label": q["label"],
                "type": q["type"],
                "options": [
                    {"option": opt, "percent": round(opt_pct.get(opt, 0.0), 1)}
                    for opt in options
                ],
                "skipped_percent": skipped_percent,
                "grid_id": q.get("grid_id"),
                "grid_label": q.get("grid_label"),
                "row_label": q.get("row_label"),
            }
        )
    return result


def compute_preview(strategy: dict, config: dict) -> dict:
    """Build the preview payload: persona summaries, per-question per-persona weights,
    and the initial aggregate distributions (all personas selected)."""
    personas = strategy.get("personas", [])
    persona_summaries = [
        {
            "code": p["code"],
            "name": p.get("name", p["code"]),
            "description": p.get("description", ""),
            "count_percent": p.get("count_percent", 0),
        }
        for p in personas
    ]

    questions_payload: list[dict] = []
    for q in select_preview_questions(config):
        per_persona = {p["code"]: persona_answer_weights(p, q["id"]) for p in personas}
        questions_payload.append(
            {
                "id": q["id"],
                "label": q["label"],
                "type": q["type"],
                "options": q.get("options", []),
                "per_persona": per_persona,
                "grid_id": q.get("grid_id"),
                "grid_label": q.get("grid_label"),
                "row_label": q.get("row_label"),
            }
        )

    distributions = aggregate_distributions(
        persona_summaries, [p["code"] for p in personas], questions_payload
    )

    return {
        "personas": persona_summaries,
        "questions": questions_payload,
        "distributions": distributions,
    }


def filter_and_renormalize_personas(strategy: dict, codes: list[str]) -> dict:
    """Return a strategy copy keeping only `codes`, with count_percent rescaled to sum 100."""
    selected = [p for p in strategy.get("personas", []) if p["code"] in codes]
    if not selected:
        raise ValueError("No personas selected")

    total = sum(p.get("count_percent", 0) for p in selected) or 1
    scaled = [p.get("count_percent", 0) / total * 100 for p in selected]
    floored = [int(x) for x in scaled]
    remainder = 100 - sum(floored)
    order = sorted(range(len(scaled)), key=lambda i: scaled[i] - floored[i], reverse=True)
    for i in range(remainder):
        floored[order[i]] += 1

    new_strategy = copy.deepcopy(strategy)
    new_personas = []
    for persona, count_percent in zip(selected, floored):
        persona = dict(persona)
        persona["count_percent"] = count_percent
        new_personas.append(persona)
    new_strategy["personas"] = new_personas
    return new_strategy
