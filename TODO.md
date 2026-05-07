# TODO — Google Forms Autofill: Implementation Plan

## Goal
Submit 100 realistic, persona-driven responses to the Google Form:
`https://docs.google.com/forms/d/e/1FAIpQLScTqX0Lz4l1Yh2STGx-S_64yw5TYYlrQ4KQxrYXORsEBlX24w/viewform`

Response generation strategy (personas, distributions, coherence rules) is in `STRATEGY.md`.

---

## Technical Stack

- **Language**: Python 3.11+
- **Browser automation**: Playwright (`playwright` + `playwright-python`) — UI automation, not HTTP POST
  - Handles multi-page Google Forms naturally
  - Selects elements by visible label text — robust to DOM changes
  - Supports headless and headed (visible) mode
- **Data source**: `responses.json` — 100 pre-generated response objects produced by `generator.py`
- **Execution**: Sequential submissions, random 5–20 second delay between each

## File Structure

```
forms-autofill/
├── STRATEGY.md        ← personas, distributions, coherence rules (do not edit for impl)
├── TODO.md            ← this file
├── generator.py       ← generates responses.json from persona templates + coherence rules
├── responses.json     ← 100 pre-generated response objects (output of generator.py)
├── filler.py          ← FormFiller class: drives Playwright through one form submission
├── main.py            ← orchestrator: loops responses.json, applies delays, logs results
├── results.log        ← written at runtime by main.py
└── requirements.txt
```

---

## Response Object Schema

Each entry in `responses.json`:

```json
{
  "persona": "A",
  "Q1": "Mężczyzna",
  "Q2": "21-30 lat",
  "Q3": "Wyższe",
  "Q4": "Miasto od 100 tyś do 500 tyś mieszkańców",
  "Q5": "Organizacja powyżej 100 osób",
  "Q6": "Urządzenia zapewnia pracodawca",
  "Q7": ["Poczta elektroniczna", "Komunikator służbowy", "Dostęp do infrastruktury krytycznej (np. VPN)"],
  "Q8": "Tak",
  "Q9": "Tak",
  "Q10": ["Hasło/PIN/Wzór", "Odcisk palca"],
  "Q11": "Natychmiast po pojawieniu się powiadomienia",
  "Q12": "Tak, znam jej zapisy i stosuję się do nich",
  "Q13": "Tak",
  "Q14": "Nie, ale w przeszłości firmy pojawiły się takie incydenty",
  "Q15": "Tak, wielokrotnie",
  "Q16": "Nigdy",
  "Q17": "Tak",
  "Q18": 5,
  "Q19": "Nie, przepisy są zbyt ogólne lub niewystarczające",
  "Q20": 1
}
```

- **Q7, Q10** → list of strings (checkbox questions, 1–N options selected)
- **Q18, Q20** → integer 1–5 (scale questions)
- **All others** → single string (radio questions)

---

## Phase 1 — Response Generation (`generator.py`)

1. Encode each of the 6 persona templates (A–F) from `STRATEGY.md §4` as Python dicts with weighted option lists
2. Generate the required count per persona: **A=18, B=28, C=20, D=14, E=12, F=8**
3. After each response is generated, validate all **hard coherence rules** (`STRATEGY.md §5`); re-sample on violation:
   1. Q10 `"Brak zabezpieczeń"` is mutually exclusive with all other Q10 options
   2. If Q13=`"Tak"` → Q11 ≠ `"Nigdy albo jak przez przypadek kliknę aktualizację"`
   3. If Q12=`"Tak, znam jej zapisy i stosuję się do nich"` → Q9 ≠ `"Nie"`
   4. If Q8=`"Tak"` → Q6=`"Urządzenia zapewnia pracodawca"` (90% of cases; re-sample remaining 10%)
   5. If Q17=`"Tak"` → Q18 ≥ 2
   6. If Q7 includes VPN → Q8 ≠ `"Nie"` (for high-awareness personas A, F)
4. Soft rules (`STRATEGY.md §5` table) are encoded as weighted probabilities inside persona templates, not post-hoc validators
5. Shuffle final 100-entry list to interleave personas
6. Write to `responses.json`

### Validation commands after generation

```bash
python -c "import json; d=json.load(open('responses.json')); print(len(d))"
python -c "import json,collections; d=json.load(open('responses.json')); print(dict(collections.Counter(r['persona'] for r in d)))"
python -c "import json,collections; d=json.load(open('responses.json')); print(dict(collections.Counter(r['Q1'] for r in d)))"
```

Expected: 100 total, `{'A':18,'B':28,'C':20,'D':14,'E':12,'F':8}`, `{'Mężczyzna':50,'Kobieta':50}`

---

## Phase 2 — Form Filler (`filler.py`)

`FormFiller` class with a `submit(page, response: dict)` method:

- Navigate to the form URL on a **fresh page** per submission (no session bleed between responses)
- The form is **multi-page** — fill each page's visible questions, then click "Dalej"; click "Prześlij" on the final page
- Wait for the confirmation screen; raise a descriptive exception on unexpected state

### Playwright Selector Strategy

| Question type | Approach |
|---|---|
| Radio (Q1–Q6, Q8–Q9, Q11–Q17, Q19) | `page.locator('div[role="radio"]').filter(has_text=option).click()` |
| Checkbox (Q7, Q10) | Same locator, iterate over each string in the list |
| Scale 1–5 (Q18, Q20) | Locate scale widget, click the radio whose aria-label or position matches the integer |
| Next page | `page.get_by_role("button", name=re.compile("Dalej\|Next"))` |
| Submit | `page.get_by_role("button", name=re.compile("Prześlij\|Submit"))` |

---

## Phase 3 — Orchestration (`main.py`)

### CLI

```
python main.py [--headless] [--start N] [--delay-min S] [--delay-max S]
```

| Argument | Default | Description |
|---|---|---|
| `--headless` | off (visible window) | Run browser without UI |
| `--start N` | 0 | Resume from response index N |
| `--delay-min S` | 5 | Min seconds between submissions |
| `--delay-max S` | 20 | Max seconds between submissions |

### Behaviour

- Load `responses.json`, slice from `--start`
- For each response: call `filler.submit()`, sleep random delay in `[delay-min, delay-max]`, log index + persona + status to stdout and `results.log`
- On exception: log error + response index, continue to next (do not abort the run)

---

## Phase 4 — End-to-End Run

```bash
# 1. Install deps
pip install playwright && playwright install chromium

# 2. Generate responses
python generator.py

# 3. Test one submission (visible window, no delay)
python main.py --start 0 --delay-min 0 --delay-max 0
# Stop after first submission; verify it appears in Google Forms responses tab

# 4. Full run (headless)
python main.py --headless
# If interrupted at index N: python main.py --headless --start N
```

After completion: open Google Forms responses tab and verify totals match `STRATEGY.md §3` distribution tables.

---

## Anti-Bot Notes

- 5–20 second random delay keeps rate ≤ ~12 submissions/min
- No User-Agent rotation needed at this scale for anonymous Google Forms
- Do **not** use direct HTTP POST — entry IDs are fragile; UI automation is more maintainable

---

## Progress Tracker

- [ ] `generator.py` written
- [ ] `responses.json` generated and validated
- [ ] `filler.py` written
- [ ] Single-submission test passed (visible mode)
- [ ] `main.py` written
- [ ] `requirements.txt` written
- [ ] Full 100-submission run completed
- [ ] Distribution verified in Google Forms
