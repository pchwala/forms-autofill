"""new_filler.py — Submits Google Form responses via HTTP requests (no browser)."""

from __future__ import annotations

import json
import random
import sys
import time

import requests

FORM_RESPONSE_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLScTqX0Lz4l1Yh2STGx-S_64yw5TYYlrQ4KQxrYXORsEBlX24w/formResponse"
)

# Maps question ID → Google Forms entry ID (extracted from form_source.html).
_ENTRY_IDS: dict[str, str] = {
    "Q1":  "entry.1223506545",
    "Q2":  "entry.1942252282",
    "Q3":  "entry.1905423568",
    "Q4":  "entry.1983749556",
    "Q5":  "entry.742126363",
    "Q6":  "entry.441848207",
    "Q7":  "entry.2004769140",
    "Q8":  "entry.342350116",
    "Q9":  "entry.938373020",
    "Q10": "entry.1478590826",
    "Q11": "entry.938208733",
    "Q12": "entry.1500003085",
    "Q13": "entry.684137257",
    "Q14": "entry.1169750823",
    "Q15": "entry.100867800",
    "Q16": "entry.1906427002",
    "Q17": "entry.398179910",
    "Q18": "entry.1808091593",
    "Q19": "entry.708444986",
    "Q20": "entry.413783070",
}

# Questions whose response values are lists of strings (Google Forms checkboxes).
_CHECKBOX_QUESTIONS = {"Q7", "Q10"}

# Questions whose response values are integers 1–5 (Google Forms linear scale).
_SCALE_QUESTIONS = {"Q18", "Q20"}


class FormFiller:
    """Fills and submits one response to the Google Form via HTTP POST."""

    def submit(self, session: requests.Session, response: dict) -> None:
        """Build form payload and POST it to the formResponse endpoint.

        Args:
            session: A requests.Session to reuse connections across submissions.
            response: A response dict matching the schema in responses.json.

        Raises:
            RuntimeError: If the submission confirmation is not detected.
        """
        # Use a list of tuples so repeated keys work for checkbox questions.
        payload: list[tuple[str, str]] = []

        for qid in (f"Q{n}" for n in range(1, 21)):
            value = response.get(qid)
            if value is None:
                continue

            entry_key = _ENTRY_IDS[qid]

            if qid in _CHECKBOX_QUESTIONS:
                # Each selected option is a separate field with the same key.
                for option in value:
                    payload.append((entry_key, option))
            elif qid in _SCALE_QUESTIONS:
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
            FORM_RESPONSE_URL,
            data=payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": FORM_RESPONSE_URL.replace("formResponse", "viewform"),
                "Origin": "https://docs.google.com",
            },
            allow_redirects=True,
            timeout=30,
        )

        if "formResponse" not in resp.url:
            raise RuntimeError(
                f"Submission confirmation not detected — "
                f"final URL was {resp.url!r} (HTTP {resp.status_code})."
            )


def submit_range(responses: list, start: int, count: int) -> None:
    """Submit *count* responses from *responses* beginning at *start*.

    Args:
        responses: Full list of response dicts loaded from JSON.
        start: Index of the first response to submit (0-based).
        count: How many responses to submit.
    """
    subset = responses[start: start + count]
    filler = FormFiller()

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
                filler.submit(session, response)
                print("  ✓ Submitted.")
            except RuntimeError as exc:
                print(f"  ✗ Failed: {exc}")

            # Small random delay to avoid triggering spam detection.
            if i < start + len(subset) - 1:
                time.sleep(random.uniform(0.5, 1.5))


def main() -> None:
    input_file = sys.argv[1] if len(sys.argv) > 1 else "responses.json"
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 1

    with open(input_file, encoding="utf-8") as f:
        responses = json.load(f)

    submit_range(responses, start, count)


if __name__ == "__main__":
    main()
