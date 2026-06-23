from __future__ import annotations

import hashlib
import json
import math
import pathlib
import random
from typing import Callable

import backend.firestore_service as firestore_service
import backend.forms_extractor as forms_extractor
import backend.strategy_generator as sg_module
from backend.response_generator import ResponseGenerator
from backend.new_filler import FormFiller

Emit = Callable[[dict], None]

MAX_AI_RESPONSES = 200


def step1_extract(
    form_url: str,
    data_dir: pathlib.Path,
    emit: Emit,
) -> tuple[pathlib.Path, str]:
    emit({"type": "step", "step": 1, "status": "start", "message": "Pobieranie pytań z formularza"})
    config_path, base_name = forms_extractor.extract(
        form_url=form_url,
        output_file="data/responses.json",
        strategy_file="data/strategy.json",
        data_dir=data_dir,
    )
    emit({"type": "step", "step": 1, "status": "done", "message": "Formularz pobrany."})
    return config_path, base_name


def _strategy_cache_key(
    form_url: str, desire_prompt: str | None
) -> tuple[str, str] | None:
    """Return (form_id, cache_key) for the global strategy cache, or None if no form id.

    The key folds in the optional desire_prompt: the same form with no/identical prompt
    reuses the cached strategy, while a different prompt regenerates (its distributions
    differ).
    """
    form_id = forms_extractor.extract_form_id(form_url)
    if not form_id:
        return None
    norm = (desire_prompt or "").strip().lower()
    desire_hash = hashlib.sha256(norm.encode()).hexdigest()[:16] if norm else "default"
    return form_id, f"{form_id}__{desire_hash}"


def step2_strategy(
    config_path: pathlib.Path,
    emit: Emit,
    pipeline_id: str | None = None,
    desire_prompt: str | None = None,
) -> pathlib.Path:
    base_name = config_path.name[: -len("_form_config.json")]
    data_dir = config_path.parent
    config_data = json.loads(config_path.read_text(encoding="utf-8"))
    keys = _strategy_cache_key(config_data.get("form_url", ""), desire_prompt)
    cache_key = keys[1] if keys else None

    # Cache hit: reuse the previously generated research + strategy (no GPT calls).
    cached = firestore_service.get_cached_strategy(cache_key) if cache_key else None
    if cached:
        emit({"type": "step", "step": 2, "status": "start", "message": "Wczytywanie zapisanej strategii"})
        strategy_data = cached.get("strategy")
        strategy_path = data_dir / f"{base_name}_strategy.json"
        strategy_path.write_text(
            json.dumps(strategy_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        emit({"type": "result", "key": "strategy", "data": strategy_data})
        emit({"type": "step", "step": 2, "status": "done", "message": "Strategia wczytana z pamięci."})
        for step_key in ("research_basis", "research_analysis", "strategy"):
            value = cached.get(step_key)
            if value is not None:
                firestore_service.save_pipeline_step(pipeline_id, step_key, value)
        return strategy_path

    # Cache miss: run the 3-step GPT pipeline, persist per-pipeline, then populate the cache.
    emit({"type": "step", "step": 2, "status": "start", "message": "Generowanie strategii (3 kroki GPT)"})
    strategy_path = sg_module.run(config_path=config_path, emit=emit, desire_prompt=desire_prompt)
    strategy_data = json.loads(strategy_path.read_text(encoding="utf-8"))
    emit({"type": "result", "key": "strategy", "data": strategy_data})
    emit({"type": "step", "step": 2, "status": "done", "message": "Strategia zapisana."})
    steps: dict[str, object] = {}
    for step_key, suffix in [
        ("research_basis", "_research_basis.json"),
        ("research_analysis", "_research_analysis.json"),
        ("strategy", "_strategy.json"),
    ]:
        fp = data_dir / f"{base_name}{suffix}"
        if fp.exists():
            data = json.loads(fp.read_text(encoding="utf-8"))
            steps[step_key] = data
            firestore_service.save_pipeline_step(pipeline_id, step_key, data)

    if keys and "strategy" in steps:
        form_id, cache_key = keys
        firestore_service.save_cached_strategy(
            cache_key,
            form_id=form_id,
            form_url=config_data.get("form_url", ""),
            desire_prompt=desire_prompt,
            strategy=steps.get("strategy"),
            research_basis=steps.get("research_basis"),
            research_analysis=steps.get("research_analysis"),
        )
    return strategy_path


def step3_generate(
    form_config: dict,
    strategy: dict,
    total_responses: int,
    emit: Emit,
    pipeline_id: str | None = None,
) -> list[dict]:
    ai_count = min(total_responses, MAX_AI_RESPONSES)
    suffix = f" (ponownie użyte w partiach, łącznie {total_responses})" if total_responses > ai_count else ""
    emit({"type": "step", "step": 3, "status": "start", "message": f"Generowanie {ai_count} odpowiedzi AI{suffix}"})
    config = {**form_config, "total_responses": ai_count}
    responses = ResponseGenerator(config).generate(emit=emit, strategy=strategy)
    emit({"type": "result", "key": "responses", "data": responses})
    emit({"type": "step", "step": 3, "status": "done", "message": f"Wygenerowano {len(responses)} odpowiedzi AI{suffix}"})
    firestore_service.save_pipeline_step(pipeline_id, "responses", responses)
    return responses


def step4_shuffle(
    responses: list[dict],
    emit: Emit,
) -> list[dict]:
    emit({"type": "step", "step": 4, "status": "start", "message": "Mieszanie odpowiedzi"})
    shuffled = list(responses)
    random.shuffle(shuffled)
    emit({"type": "step", "step": 4, "status": "done", "message": "Odpowiedzi wymieszane"})
    return shuffled


def step5_submit(
    form_config: dict,
    responses: list[dict],
    total_responses: int,
    emit: Emit,
) -> int:
    """Submit responses (looping in batches when total_responses exceeds the unique count).

    Returns the number of responses that were confirmed as submitted — this is what the
    user is charged for (1 credit per confirmed submission).
    """
    total_batches = math.ceil(total_responses / len(responses))
    emit({
        "type": "step",
        "step": 5,
        "status": "start",
        "message": f"Wysyłanie {total_responses} odpowiedzi w {total_batches} partiach",
    })
    filler = FormFiller(form_config)
    submitted = 0
    succeeded = 0
    current_responses = list(responses)

    for batch in range(1, total_batches + 1):
        remaining = total_responses - submitted
        batch_size = min(len(current_responses), remaining)
        batch_offset = submitted

        emit({"type": "message", "text": f"Partia {batch}/{total_batches}: wysyłanie {batch_size} odpowiedzi"})

        def _batch_emit(event: dict, _offset: int = batch_offset, _total: int = total_responses) -> None:
            if event.get("type") == "submit_progress":
                emit({
                    **event,
                    "current": _offset + event["current"],
                    "total": _total,
                    "batch": batch,
                    "total_batches": total_batches,
                })
            else:
                emit(event)

        succeeded += filler.submit_range(current_responses, 0, batch_size, emit=_batch_emit)
        submitted += batch_size

        if submitted < total_responses:
            # Shuffle for the next batch
            random.shuffle(current_responses)

    emit({"type": "step", "step": 5, "status": "done", "message": f"{succeeded}/{submitted} odpowiedzi wysłanych"})
    return succeeded
