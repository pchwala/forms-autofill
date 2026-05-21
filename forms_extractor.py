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

# Google Forms internal type_id for section/page dividers.
_SECTION_TYPE = 8


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


def _extract_structure(
    fb_data: list,
) -> tuple[str, list[dict], list[dict], list[dict]]:
    """Parse FB_PUBLIC_LOAD_DATA_ and return (form_title, pages, questions, routing).

    FB_PUBLIC_LOAD_DATA_ structure (top-level):
      [version, form_descriptor, ...]

    form_descriptor:
      [form_id, items, null, ..., form_title, ...]
        index:    0      1              8

    Each item in items:
      [item_id, title, description, type_id, response_groups, ...]

    Section dividers (type_id == 8) separate pages; they carry no response data.

    Each response_group (first group carries entry info for single-field questions):
      [entry_id, options, required, ...]

    Each option:
      [option_text, extra, go_to, extra, flag]
      where go_to at index [2]:
        None / 0  → normal flow (no special routing)
        -2        → go to next page
        -3        → submit form immediately (terminal)
        <int>     → jump to section whose item_id equals this value

    Returns:
        form_title  – string title of the form
        pages       – ordered list of page dicts (id, section_id, title,
                      description, question_ids)
        questions   – ordered list of question dicts (same schema as before,
                      each with an added "page" field)
        routing     – list of routing-rule dicts for questions that have
                      conditional navigation; each condition carries
                      skipped_question_ids (computed by _compute_routing_skips)
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

    # ── Pass 1: separate raw items into pages using section dividers ───────────
    # Each "page" is a (section_info_dict, [item, ...]) pair.
    raw_pages: list[tuple[dict, list]] = []
    cur_section: dict = {"section_id": None, "title": "", "description": ""}
    cur_items: list = []

    for item in raw_items:
        if not isinstance(item, list) or len(item) < 4:
            continue
        if item[3] == _SECTION_TYPE:
            raw_pages.append((cur_section, cur_items))
            cur_section = {
                "section_id": item[0],
                "title": str(item[1]) if item[1] else "",
                "description": str(item[2]) if len(item) > 2 and item[2] else "",
            }
            cur_items = []
        else:
            cur_items.append(item)
    raw_pages.append((cur_section, cur_items))  # flush final page

    # Map section_id (item[0] of a type-8 item) → page index, for jump resolution.
    section_to_page_idx: dict[int, int] = {
        sec["section_id"]: idx
        for idx, (sec, _) in enumerate(raw_pages)
        if sec["section_id"] is not None
    }

    # ── Pass 2: extract questions, page assignments, and option routing ─────────
    pages: list[dict] = []
    questions: list[dict] = []
    routing: list[dict] = []
    q_index = 1

    for page_idx, (sec_info, items) in enumerate(raw_pages):
        page_id = f"page_{page_idx + 1}"
        q_ids_in_page: list[str] = []

        for item in items:
            type_id: int = item[3]
            config_type = GOOGLE_TYPE_MAP.get(type_id)
            if config_type is None or config_type == "grid":
                continue

            response_groups: list = (
                item[4] if len(item) > 4 and isinstance(item[4], list) else []
            )
            if not response_groups:
                continue

            group = response_groups[0]
            if not isinstance(group, list) or len(group) < 1:
                continue

            entry_id_num = group[0]
            raw_options: list = (
                group[1] if len(group) > 1 and isinstance(group[1], list) else []
            )
            required_flag = bool(group[2]) if len(group) > 2 and group[2] else False

            q_id = f"Q{q_index}"
            options_plain: list[str] = []
            option_routing: list[dict] = []
            has_routing = False

            for opt in raw_options:
                if not isinstance(opt, list) or not opt or opt[0] is None:
                    continue
                opt_text = str(opt[0])
                options_plain.append(opt_text)

                # Index [2] of each option encodes the go-to target.
                go_to_raw = opt[2] if len(opt) > 2 else None
                if go_to_raw is None or go_to_raw == 0:
                    go_to = None
                elif go_to_raw == -2:
                    go_to = "next_page"
                    has_routing = True
                elif go_to_raw == -3:
                    go_to = "submit"
                    has_routing = True
                else:
                    # Positive int: jump to the section whose item_id equals go_to_raw.
                    target_idx = section_to_page_idx.get(go_to_raw)
                    go_to = (
                        f"page_{target_idx + 1}"
                        if target_idx is not None
                        else f"section:{go_to_raw}"
                    )
                    has_routing = True

                option_routing.append({"value": opt_text, "go_to": go_to})

            question: dict = {
                "id": q_id,
                "label": str(item[1]) if item[1] else "",
                "entry_id": f"entry.{entry_id_num}",
                "type": config_type,
                "required": required_flag,
                "page": page_id,
            }
            if options_plain and config_type not in FREE_TEXT_TYPES:
                question["options"] = options_plain

            questions.append(question)
            q_ids_in_page.append(q_id)

            if has_routing:
                routing.append({
                    "question_id": q_id,
                    "entry_id": f"entry.{entry_id_num}",
                    "label": str(item[1]) if item[1] else "",
                    "conditions": option_routing,
                })

            q_index += 1

        page_obj: dict = {
            "id": page_id,
            "section_id": sec_info["section_id"],
            "title": sec_info["title"],
            "question_ids": q_ids_in_page,
        }
        if sec_info["description"]:
            page_obj["description"] = sec_info["description"]
        pages.append(page_obj)

    return form_title, pages, questions, routing


def _compute_routing_skips(
    routing: list[dict], pages: list[dict]
) -> list[dict]:
    """Augment each routing condition with skipped_question_ids.

    For every option that causes a page jump or form submission, computes which
    question IDs would be bypassed and stores them on the condition dict.
    Mutates *routing* in-place and returns it for convenience.
    """
    page_idx_map = {p["id"]: i for i, p in enumerate(pages)}
    q_to_page_id: dict[str, str] = {
        q_id: p["id"]
        for p in pages
        for q_id in p["question_ids"]
    }

    for rule in routing:
        q_page_id = q_to_page_id.get(rule["question_id"], "")
        q_page_idx = page_idx_map.get(q_page_id, 0)

        for cond in rule["conditions"]:
            go_to = cond["go_to"]

            if go_to is None or go_to == "next_page":
                cond["skipped_question_ids"] = []

            elif go_to == "submit":
                # Every question on subsequent pages is skipped.
                skipped: list[str] = []
                for p in pages[q_page_idx + 1:]:
                    skipped.extend(p["question_ids"])
                cond["skipped_question_ids"] = skipped

            elif go_to.startswith("page_"):
                # Questions on pages between current+1 and target-1 are skipped.
                target_idx = page_idx_map.get(go_to, q_page_idx + 1)
                skipped = []
                for p in pages[q_page_idx + 1:target_idx]:
                    skipped.extend(p["question_ids"])
                cond["skipped_question_ids"] = skipped

            else:
                cond["skipped_question_ids"] = []

    return routing


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

    form_title, pages, questions, routing = _extract_structure(fb_data)
    _compute_routing_skips(routing, pages)

    print(
        f"Extracted {len(questions)} question(s) from '{form_title}' "
        f"across {len(pages)} page(s)"
    )
    if routing:
        print(f"  Routing rules found on {len(routing)} question(s)")

    config = {
        "form_url": form_url,
        "form_response_url": _derive_response_url(form_url),
        "form_title": form_title,
        "output_file": output_file,
        "strategy_file": strategy_file,
        "model": model,
        "personas": [],
        "pages": pages,
        "routing": routing,
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
