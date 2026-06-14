"""new_filler.py — Submits Google Form responses via HTTP requests (no browser)."""

from __future__ import annotations

import json
import pathlib
import random
import sys
import time

import requests
from typing import Callable


class FormFiller:
    """Fills and submits responses to a Google Form via HTTP POST.

    All form-specific data (URL, entry IDs, question types) is read from a
    config dict, typically loaded from a per-form JSON file.
    """

    def __init__(self, config: dict) -> None:
        self._form_response_url: str = config["form_response_url"]
        questions = config["questions"]
        # Preserve question order from config so the POST payload is ordered.
        self._entry_ids: dict[str, str] = {q["id"]: q["entry_id"] for q in questions}
        self._checkbox_questions: set[str] = {
            q["id"] for q in questions if q["type"] == "checkbox"
        }
        self._scale_questions: set[str] = {
            q["id"] for q in questions if q["type"] == "scale"
        }

    def submit(self, session: requests.Session, response: dict) -> None:
        """Build form payload and POST it to the formResponse endpoint.

        Args:
            session: A requests.Session to reuse connections across submissions.
            response: A response dict matching the schema in the config's output_file.

        Raises:
            RuntimeError: If the submission confirmation is not detected.
        """
        # Use a list of tuples so repeated keys work for checkbox questions.
        payload: list[tuple[str, str]] = []

        for qid, entry_key in self._entry_ids.items():
            value = response.get(qid)
            if value is None:
                continue

            if qid in self._checkbox_questions:
                # Each selected option is a separate field with the same key.
                for option in value:
                    payload.append((entry_key, option))
            elif qid in self._scale_questions:
                payload.append((entry_key, str(int(value))))
            else:
                payload.append((entry_key, str(value)))

        # Standard hidden fields that Google Forms includes in every submission.
        fbzx = random.randint(-(2**63), 2**63 - 1)
        payload += [
            ("fvv", "1"),
            ("draftResponse", "[]"),
            ("pageHistory", "0"),
            ("fbzx", str(fbzx)),
        ]

        resp = session.post(
            self._form_response_url,
            data=payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": self._form_response_url.replace("formResponse", "viewform"),
                "Origin": "https://docs.google.com",
            },
            allow_redirects=True,
            timeout=30,
        )

        # A successful submission lands on the formResponse confirmation page, OR
        # on viewform?edit_requested=true when the form allows response editing.
        is_confirmed = (
            "formResponse" in resp.url
            or "edit_requested=true" in resp.url
        )
        if not is_confirmed:
            raise RuntimeError(
                f"Submission confirmation not detected — "
                f"final URL was {resp.url!r} (HTTP {resp.status_code})."
            )

    def submit_range(self, responses: list, start: int, count: int, emit: Callable[[dict], None] | None = None) -> int:
        """Submit *count* responses from *responses* beginning at *start*.

        Args:
            responses: Full list of response dicts loaded from JSON.
            start: Index of the first response to submit (0-based).
            count: How many responses to submit.
            emit: Optional callback to stream progress events to the frontend.

        Returns:
            The number of responses that were confirmed as submitted (failures excluded).
        """
        subset = responses[start: start + count]
        succeeded = 0

        with requests.Session() as session:
            session.headers.update({
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            })

            for i, response in enumerate(subset, start=start):
                print(
                    f"[{i - start + 1}/{len(subset)}] Submitting index {i} "
                    f"(persona {response.get('persona', '?')})…"
                )
                try:
                    self.submit(session, response)
                    succeeded += 1
                    print("  ✓ Submitted.")
                except RuntimeError as exc:
                    print(f"  ✗ Failed: {exc}")

                if emit is not None:
                    emit({"type": "submit_progress", "current": i - start + 1, "total": len(subset)})

                # Small random delay to avoid triggering spam detection.
                if i < start + len(subset) - 1:
                    time.sleep(random.uniform(0.5, 1.5))

        return succeeded


def main() -> None:
    config_path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "data/form_config.json")
    config = json.loads(config_path.read_text(encoding="utf-8"))

    responses_path = sys.argv[2] if len(sys.argv) > 2 else config.get("output_file", "data/responses.json")
    start = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    count = int(sys.argv[4]) if len(sys.argv) > 4 else 1

    with open(responses_path, encoding="utf-8") as f:
        responses = json.load(f)

    FormFiller(config).submit_range(responses, start, count)


if __name__ == "__main__":
    main()
