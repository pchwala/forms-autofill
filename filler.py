"""filler.py — Drives a single Google Form submission via Playwright."""

from __future__ import annotations

import re
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

FORM_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLScTqX0Lz4l1Yh2STGx-S_64yw5TYYlrQ4KQxrYXORsEBlX24w/viewform"
)

# Unique substrings of each question's label text used to scope interactions to
# the correct question block, avoiding ambiguity when option texts repeat
# (e.g. "Tak" appears in Q8, Q9, Q13, Q17).
_LABEL_FRAGMENTS: dict[str, str] = {
    "Q1":  "Płeć",
    "Q2":  "Wiek",
    "Q3":  "Wykształcenie",
    "Q4":  "Zamieszkanie",
    "Q5":  "Jak duże jest twoje miejsce pracy",
    "Q6":  "W jakim modelu wykorzystujesz urządzenia mobilne",
    "Q7":  "Do jakich zasobów organizacji masz dostęp",
    "Q8":  "oprogramowanie do zdalnego nim zarządzania",
    "Q9":  "procedury w przypadku utraty",
    "Q10": "metody blokady dostępu stosujesz",
    "Q11": "Jak często dokonujesz aktualizacji",
    "Q12": "istnieje i jest egzekwowana",
    "Q13": "ciągu ostatnich 12 miesięcy szkolenie",
    "Q14": "ciągu ostatnich 6 miesięcy doszło do incydentu",
    "Q15": "Mobile Phishing",
    "Q16": "otwartymi, publicznymi sieciami Wi-Fi",
    "Q17": "czym jest Krajowy System Cyberbezpieczeństwa",
    "Q18": "najsłabszym ogniwem",
    "Q19": "obecne ramy prawne",
    "Q20": "ogólny poziom odporności",
}

# Questions whose response values are lists of strings (Google Forms checkboxes).
_CHECKBOX_QUESTIONS = {"Q7", "Q10"}

# Questions whose response values are integers 1–5 (Google Forms linear scale).
_SCALE_QUESTIONS = {"Q18", "Q20"}


class FormFiller:
    """Fills and submits one response to the Google Form."""

    def submit(self, page: Page, response: dict) -> None:
        """Navigate to the form, fill every question, and click submit.

        Args:
            page: A Playwright Page (caller owns the browser/context lifetime).
            response: A response dict matching the schema in TODO.md.

        Raises:
            RuntimeError: If the submission confirmation is not detected.
        """
        page.goto(FORM_URL, wait_until="domcontentloaded")
        # Wait until Google Forms JS has enabled the inputs (they start aria-disabled="true").
        page.wait_for_selector(
            '[role="radio"]:not([aria-disabled="true"]), [role="checkbox"]:not([aria-disabled="true"])',
            timeout=20_000,
        )

        for qid in (f"Q{n}" for n in range(1, 21)):
            value = response.get(qid)
            if value is None:
                continue

            # Scope all interactions to the block containing this question's label.
            fragment = _LABEL_FRAGMENTS[qid]
            block = page.locator('div[role="listitem"]').filter(
                has_text=re.compile(re.escape(fragment))
            )

            if qid in _SCALE_QUESTIONS:
                # Scale radios carry no text — click by position (0-based index).
                block.locator('div[role="radio"]').nth(int(value) - 1).click()

            elif qid in _CHECKBOX_QUESTIONS:
                # Checkboxes: click each selected option by its visible label text.
                for option in value:
                    block.locator('div[role="checkbox"]').filter(
                        has_text=re.compile(re.escape(option))
                    ).click()

            else:
                # Radio: click the single option matching the response value.
                block.locator('div[role="radio"]').filter(
                    has_text=re.compile(re.escape(str(value)))
                ).click()

        # Click the submit button (label is "Prześlij" in Polish).
        page.get_by_role("button", name=re.compile(r"Prześlij|Submit")).click()

        # Google Forms redirects to /formResponse on successful submission.
        try:
            page.wait_for_url(re.compile(r"formResponse"), timeout=15_000)
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(
                "Submission confirmation not detected — "
                "the form may not have submitted correctly."
            ) from exc


def submit_range(responses: list, start: int, count: int) -> None:
    """Submit *count* responses from *responses* beginning at *start*.

    Args:
        responses: Full list of response dicts loaded from JSON.
        start: Index of the first response to submit (0-based).
        count: How many responses to submit.
    """
    from playwright.sync_api import sync_playwright

    subset = responses[start: start + count]
    filler = FormFiller()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--lang=pl-PL"],
        )
        context = browser.new_context(locale="pl-PL")
        for i, response in enumerate(subset, start=start):
            print(f"[{i - start + 1}/{len(subset)}] Submitting index {i} (persona {response.get('persona', '?')})…")
            page = context.new_page()
            try:
                filler.submit(page, response)
                print(f"  ✓ Submitted.")
            finally:
                page.close()
        context.close()
        browser.close()


def main() -> None:
    import json
    import sys

    input_file = sys.argv[1] if len(sys.argv) > 1 else "responses.json"
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 1

    with open(input_file, encoding="utf-8") as f:
        responses = json.load(f)

    submit_range(responses, start, count)


if __name__ == "__main__":
    main()
