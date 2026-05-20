"""forms_extractor.py — Extracts questions from a public Google Form and writes a form_config_N.json."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

import requests


# Maps Google Forms internal type_id to the config schema type string.
# Section dividers (type 6) are intentionally absent — they are skipped.
GOOGLE_TYPE_MAP: dict[int, str] = {
    0: "text",      # Short answer
    1: "textarea",  # Paragraph
    2: "radio",     # Multiple choice
    3: "checkbox",  # Checkboxes
    4: "dropdown",  # Dropdown
    5: "scale",     # Linear scale
    7: "grid",      # Multiple choice grid (skipped — needs special handling)
    8: "date",      # Date
    9: "time",      # Time
}

# Types where an "options" field is not meaningful / not included in output.
FREE_TEXT_TYPES = {"text", "textarea", "date", "time"}


def _next_config_path(data_dir: pathlib.Path) -> pathlib.Path:
    """Return data/form_config_N.json where N is the next available number."""
    existing = sorted(
        int(m.group(1))
        for p in data_dir.glob("form_config_*.json")
        if (m := re.match(r"form_config_(\d+)\.json", p.name))
    )
    n = (existing[-1] + 1) if existing else 1
    return data_dir / f"form_config_{n}.json"


def _fetch_form_data(form_url: str) -> list:
    """Fetch the Google Form page and return the parsed FB_PUBLIC_LOAD_DATA_ array."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }
    resp = requests.get(form_url, headers=headers, timeout=30)
    resp.raise_for_status()

    marker = "var FB_PUBLIC_LOAD_DATA_ = "
    idx = resp.text.find(marker)
    if idx == -1:
        raise ValueError(
            "Could not find FB_PUBLIC_LOAD_DATA_ in the form page. "
            "Make sure the form is public and the URL is a /viewform URL."
        )

    start = idx + len(marker)
    # Use raw_decode so we stop exactly at the end of the JSON array,
    # regardless of what follows (semicolons, script tags, etc.).
    decoder = json.JSONDecoder()
    data, _ = decoder.raw_decode(resp.text[start:])
    return data


def _derive_response_url(form_url: str) -> str:
    """Derive the formResponse submission URL from a viewform URL."""
    # Strip query string and fragment before replacing the path suffix.
    base = form_url.split("?")[0].split("#")[0]
    return base.replace("viewform", "formResponse")


def _extract_questions(fb_data: list) -> tuple[str, list[dict]]:
    """Parse FB_PUBLIC_LOAD_DATA_ and return (form_title, questions).

    FB_PUBLIC_LOAD_DATA_ structure (top-level):
      [version, form_descriptor, ...]

    form_descriptor:
      [form_id, items, null, ..., form_title, description, ...]
        index:    0      1              8

    Each item in items:
      [item_id, title, description, type_id, response_groups, ...]

    Each response_group (first one carries the entry info for single-field questions):
      [entry_id, options, required, ...]

    Each option:
      [option_text, ...]
    """
    try:
        form_descriptor: list = fb_data[1]
    except (IndexError, TypeError) as exc:
        raise ValueError(f"Unexpected FB_PUBLIC_LOAD_DATA_ structure: {exc}") from exc

    form_title: str = ""
    if len(form_descriptor) > 8 and isinstance(form_descriptor[8], str):
        form_title = form_descriptor[8]

    raw_items: list = []
    if len(form_descriptor) > 1 and isinstance(form_descriptor[1], list):
        raw_items = form_descriptor[1]

    questions: list[dict] = []
    q_index = 1

    for item in raw_items:
        if not isinstance(item, list) or len(item) < 4:
            continue

        type_id: int = item[3]
        config_type = GOOGLE_TYPE_MAP.get(type_id)

        # Skip section dividers (not in map) and grid questions (need special handling).
        if config_type is None or config_type == "grid":
            continue

        response_groups: list = (
            item[4] if len(item) > 4 and isinstance(item[4], list) else []
        )
        if not response_groups:
            continue

        # The first response group holds the entry ID, options, and required flag.
        group = response_groups[0]
        if not isinstance(group, list) or len(group) < 1:
            continue

        entry_id_num = group[0]
        raw_options: list = (
            group[1] if len(group) > 1 and isinstance(group[1], list) else []
        )
        required_flag = bool(group[2]) if len(group) > 2 and group[2] else False

        options = [
            str(opt[0])
            for opt in raw_options
            if isinstance(opt, list) and opt and opt[0] is not None
        ]

        question: dict = {
            "id": f"Q{q_index}",
            "label": str(item[1]) if item[1] else "",
            "entry_id": f"entry.{entry_id_num}",
            "type": config_type,
            "required": required_flag,
        }

        if options and config_type not in FREE_TEXT_TYPES:
            question["options"] = options

        questions.append(question)
        q_index += 1

    return form_title, questions


def extract(
    form_url: str,
    model: str,
    output_file: str,
    strategy_file: str,
    data_dir: pathlib.Path,
) -> pathlib.Path:
    """Full extraction pipeline: fetch → parse → write config.

    Returns:
        Path to the written form_config_N.json file.
    """
    print(f"Fetching form: {form_url}")
    fb_data = _fetch_form_data(form_url)

    form_title, questions = _extract_questions(fb_data)
    print(f"Extracted {len(questions)} question(s) from '{form_title}'")

    config = {
        "form_url": form_url,
        "form_response_url": _derive_response_url(form_url),
        "form_title": form_title,
        "output_file": output_file,
        "strategy_file": strategy_file,
        "model": model,
        "personas": [],
        "questions": questions,
    }

    out_path = _next_config_path(data_dir)
    out_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Config written to: {out_path}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Extract all questions from a public Google Form and write a "
            "data/form_config_N.json ready for response generation."
        )
    )
    parser.add_argument("form_url", help="Full /viewform URL of the Google Form.")
    parser.add_argument(
        "--model",
        default="gpt-4.1",
        help="AI model identifier to embed in the config (default: gpt-4.1).",
    )
    parser.add_argument(
        "--output-file",
        default="data/responses.json",
        help="Responses output path to embed in the config (default: data/responses.json).",
    )
    parser.add_argument(
        "--strategy-file",
        default="STRATEGY.md",
        help="Strategy file path to embed in the config (default: STRATEGY.md).",
    )
    args = parser.parse_args()

    data_dir = pathlib.Path("data")
    data_dir.mkdir(exist_ok=True)

    try:
        extract(
            form_url=args.form_url,
            model=args.model,
            output_file=args.output_file,
            strategy_file=args.strategy_file,
            data_dir=data_dir,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
