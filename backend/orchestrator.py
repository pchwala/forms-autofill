from __future__ import annotations

import json
import math
import pathlib
import random
import time
from typing import Callable

from anyio import sleep

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
) -> pathlib.Path:
    emit({"type": "step", "step": 1, "status": "start", "message": "Extracting form questions"})
    #time.sleep(200)
    config_path = forms_extractor.extract(
        form_url=form_url,
        output_file="data/responses.json",
        strategy_file="data/strategy.json",
        data_dir=data_dir,
    )
    emit({"type": "step", "step": 1, "status": "done", "message": f"Form extracted."})
    return config_path


def step2_strategy(
    config_path: pathlib.Path,
    emit: Emit,
) -> pathlib.Path:
    emit({"type": "step", "step": 2, "status": "start", "message": "Generating strategy (3 GPT steps)"})
    strategy_path = sg_module.run(config_path=config_path, emit=emit)
    strategy_data = json.loads(strategy_path.read_text(encoding="utf-8"))
    emit({"type": "result", "key": "strategy", "data": strategy_data})
    emit({"type": "step", "step": 2, "status": "done", "message": f"Strategy saved."})
    return strategy_path


def step3_generate(
    config_path: pathlib.Path,
    strategy_path: pathlib.Path,
    total_responses: int,
    emit: Emit,
) -> list[dict]:
    ai_count = min(total_responses, MAX_AI_RESPONSES)
    suffix = f" (reused in batches for {total_responses} total)" if total_responses > ai_count else ""
    emit({"type": "step", "step": 3, "status": "start", "message": f"Generating {ai_count} AI responses{suffix}"})
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["strategy_file"] = str(strategy_path)
    config["total_responses"] = ai_count
    responses = ResponseGenerator(config).generate(emit=emit)
    emit({"type": "result", "key": "responses", "data": responses})
    emit({"type": "step", "step": 3, "status": "done", "message": f"Generated {len(responses)} AI responses{suffix}"})
    return responses


def step4_shuffle(
    responses: list[dict],
    emit: Emit,
) -> list[dict]:
    emit({"type": "step", "step": 4, "status": "start", "message": "Shuffling responses"})
    shuffled = list(responses)
    random.shuffle(shuffled)
    emit({"type": "step", "step": 4, "status": "done", "message": "Responses shuffled"})
    return shuffled


def step5_submit(
    config_path: pathlib.Path,
    responses: list[dict],
    total_responses: int,
    emit: Emit,
) -> None:
    total_batches = math.ceil(total_responses / len(responses))
    emit({
        "type": "step",
        "step": 5,
        "status": "start",
        "message": f"Submitting {total_responses} responses in {total_batches} batch(es)",
    })
    config = json.loads(config_path.read_text(encoding="utf-8"))
    filler = FormFiller(config)
    submitted = 0
    current_responses = list(responses)

    for batch in range(1, total_batches + 1):
        remaining = total_responses - submitted
        batch_size = min(len(current_responses), remaining)
        batch_offset = submitted

        emit({"type": "message", "text": f"Batch {batch}/{total_batches}: submitting {batch_size} responses"})

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

        filler.submit_range(current_responses, 0, batch_size, emit=_batch_emit)
        submitted += batch_size

        if submitted < total_responses:
            # Shuffle for the next batch
            random.shuffle(current_responses)

    emit({"type": "step", "step": 5, "status": "done", "message": f"All {submitted} responses submitted"})


def run_pipeline(
    form_url: str,
    total_responses: int,
    emit: Emit,
) -> tuple[pathlib.Path, list[dict]]:
    data_dir = pathlib.Path("data")
    data_dir.mkdir(exist_ok=True)

    config_path = step1_extract(form_url, data_dir, emit)
    strategy_path = step2_strategy(config_path, emit)
    responses = step3_generate(config_path, strategy_path, total_responses, emit)
    shuffled = step4_shuffle(responses, emit)
    step5_submit(config_path, shuffled, total_responses, emit)

    return config_path, shuffled
