from __future__ import annotations

import json
import pathlib
import random
from typing import Callable

import backend.forms_extractor as forms_extractor
import backend.strategy_generator as sg_module
from backend.response_generator import ResponseGenerator
from backend.new_filler import FormFiller

Emit = Callable[[dict], None]


def step1_extract(
    form_url: str,
    model: str,
    data_dir: pathlib.Path,
    emit: Emit,
) -> pathlib.Path:
    emit({"type": "step", "step": 1, "status": "start", "message": "Extracting form questions..."})
    config_path = forms_extractor.extract(
        form_url=form_url,
        model=model,
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
    emit({"type": "step", "step": 2, "status": "start", "message": "Generating strategy (3 GPT steps)..."})
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
    emit({"type": "step", "step": 3, "status": "start", "message": f"Generating {total_responses} responses..."})
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["strategy_file"] = str(strategy_path)
    config["total_responses"] = total_responses
    responses = ResponseGenerator(config).generate(emit=emit)
    emit({"type": "result", "key": "responses", "data": responses})
    emit({"type": "step", "step": 3, "status": "done", "message": f"Generated {len(responses)} responses"})
    return responses


def step4_shuffle(
    responses: list[dict],
    emit: Emit,
) -> list[dict]:
    emit({"type": "step", "step": 4, "status": "start", "message": "Shuffling responses..."})
    shuffled = list(responses)
    random.shuffle(shuffled)
    emit({"type": "step", "step": 4, "status": "done", "message": "Responses shuffled"})
    return shuffled


def step5_submit(
    config_path: pathlib.Path,
    responses: list[dict],
    emit: Emit,
) -> None:
    emit({"type": "step", "step": 5, "status": "start", "message": f"Submitting {len(responses)} responses to Google Form..."})
    config = json.loads(config_path.read_text(encoding="utf-8"))
    FormFiller(config).submit_range(responses, 0, len(responses), emit=emit)
    emit({"type": "step", "step": 5, "status": "done", "message": "All responses submitted"})


def run_pipeline(
    form_url: str,
    total_responses: int,
    model: str,
    emit: Emit,
) -> list[dict]:
    data_dir = pathlib.Path("data")
    data_dir.mkdir(exist_ok=True)

    config_path = step1_extract(form_url, model, data_dir, emit)
    strategy_path = step2_strategy(config_path, emit)
    responses = step3_generate(config_path, strategy_path, total_responses, emit)
    shuffled = step4_shuffle(responses, emit)
    step5_submit(config_path, shuffled, emit)

    return shuffled
