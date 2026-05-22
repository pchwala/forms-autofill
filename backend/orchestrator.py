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


def run_pipeline(
    form_url: str,
    total_responses: int,
    model: str,
    emit: Emit,
) -> list[dict]:
    data_dir = pathlib.Path("data")
    data_dir.mkdir(exist_ok=True)

    # Step 1: Extract form
    emit({"type": "step", "step": 1, "status": "start", "message": "Extracting form questions..."})
    config_path = forms_extractor.extract(
        form_url=form_url,
        model=model,
        output_file="data/responses.json",
        strategy_file="data/strategy.json",
        data_dir=data_dir,
    )
    emit({"type": "step", "step": 1, "status": "done", "message": f"Form extracted: {config_path.name}"})

    # Step 2: Generate strategy
    emit({"type": "step", "step": 2, "status": "start", "message": "Generating strategy (3 GPT steps)..."})
    strategy_path = sg_module.run(config_path=config_path)
    emit({"type": "step", "step": 2, "status": "done", "message": f"Strategy saved: {strategy_path.name}"})

    # Step 3: Generate responses
    emit({"type": "step", "step": 3, "status": "start", "message": f"Generating {total_responses} responses..."})
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["strategy_file"] = str(strategy_path)
    config["total_responses"] = total_responses
    responses = ResponseGenerator(config).generate()
    emit({"type": "step", "step": 3, "status": "done", "message": f"Generated {len(responses)} responses"})

    # Step 4: Shuffle
    emit({"type": "step", "step": 4, "status": "start", "message": "Shuffling responses..."})
    random.shuffle(responses)
    emit({"type": "step", "step": 4, "status": "done", "message": "Responses shuffled"})

    # Step 5: Submit
    emit({"type": "step", "step": 5, "status": "start", "message": f"Submitting {len(responses)} responses to Google Form..."})
    FormFiller(config).submit_range(responses, 0, len(responses))
    emit({"type": "step", "step": 5, "status": "done", "message": "All responses submitted"})

    return responses
