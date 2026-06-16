# Handoff — Anonymous Access + Preview/Paywall Product

_Last updated: 2026-06-16. Branch: `feature`._

State of the product after completing the Stripe payment integration and history
resume/resubmit features. Read this first.

---

## The product model

1. **Anonymous access** — anyone can use the site without registering (Firebase
   Anonymous Auth; upgradeable to Google via `linkWithPopup`).
2. **Free preview** — running a form does steps 1–2 only (extract → strategy). The
   user sees the generated **personas** (checkboxes to include/exclude) and the
   **predicted answer distributions** for the first ≤10 option-based questions —
   computed *from the strategy JSON*, no paid generation call.
3. **Desired-outcome prompt** — optional free-text field; injected into strategy
   generation so it skews the personas/distributions the user reviews.
4. **Paywall (credits)** — generating + submitting the real responses (steps 3–5)
   consumes credits equal to `total_responses`. Payment goes through **Stripe Checkout**
   (PLN only). Three packs available; quantity multiplier supported.

### Locked decisions
- Gating = **credits counter** (1 credit = 1 submitted response).
- Unchecking personas **renormalizes** the selected personas' `count_percent` to 100%
  (total response count stays N).
- Preview shows the **first ≤10 questions that have options**; free-text skipped.
- **History** shows `preview_ready` and `completed` entries with actionable buttons
  (Resume / Resubmit); both are credit-gated via the normal submit flow.

---

## Current backend shape (`backend/main.py`)

Ten routes:
- `POST /preview` — free; extract+strategy, returns `{job_id, pipeline_id}`, emits a
  `preview` SSE result. No credit consumed.
- `POST /pipelines/{id}/submit` — consumes credits equal to `total_responses` (**402** if
  insufficient), generates + shuffles + submits the selected personas. Credits are deducted
  *after* submission (only for responses that confirmed).
- `GET /pipelines/{id}` — restore a pipeline's preview/status from Firestore; used on
  page reload, Stripe redirect return, and history resume/resubmit. Returns `status`,
  `preview`, `total_responses`, `form_title`, `selected_persona_codes`.
- `GET /user/status` → `{credits}`.
- `GET /stream/{job_id}` — SSE drain.
- `GET /history` — list of the user's pipelines (metadata only, no step data).
- `GET /billing/packs` — returns the `PACKS` dict (no auth required).
- `POST /billing/checkout` — creates a Stripe Checkout Session; accepts `{pack, quantity}`;
  returns `{url}`. Redirects to Stripe Hosted Checkout.
- `POST /webhook/stripe` — Stripe webhook; verifies signature; fulfills
  `checkout.session.completed` by calling `add_credits` (idempotent).
- `POST /billing/confirm` — on-return fallback; confirms a session and grants credits
  idempotently (safe to call even if the webhook already ran).

**Credit packs** (`PACKS` in `main.py`, PLN only, using Stripe Price IDs):
| Pack   | Credits | PLN display | Stripe Price ID                     |
|--------|---------|-------------|-------------------------------------|
| small  | 20      | 4.99 zł     | price_1TisGhKEGI0EbMNbnbvPSCGl      |
| medium | 100     | 21.25 zł    | price_1TisGhKEGI0EbMNbf1Pg7vN6      |
| large  | 200     | 37.50 zł    | price_1TisGgKEGI0EbMNbfGVqfN4B      |

**Firestore collections**: `users/{uid}` (credits balance), `pipelines/{pipeline_id}` (full
pipeline doc including `step_form_config`, `step_strategy`, `preview`,
`selected_persona_codes`, `status`, timestamps), `credit_grants/{session_id}` (idempotency
log for Stripe fulfillment).

---

## Current frontend shape

### Billing flow
`PaywallDialog` → `POST /billing/checkout` → Stripe Hosted Checkout (PLN) →
`/?checkout=success&session_id=...` → `POST /billing/confirm` → credits granted →
preview restored from Firestore → submit auto-retried.

`POST /webhook/stripe` runs in parallel as a reliability backstop (same idempotent grant).

### History resume / resubmit
`HistoryDialog` shows all pipelines. Actionable rows:
- **`preview_ready`** → "Resume" button: calls `loadFromHistory(pipelineId)` in `usePipeline`,
  restores preview state (personas all checked by default), closes dialog.
- **`completed`** → "Resubmit" button (disabled if `credits < total_responses`): same call,
  but `selected_persona_codes` from the previous run are pre-populated in `PreviewResults`.
  User can adjust before submitting.

### Key hooks / components
- `usePipeline` (`hooks/usePipeline.ts`) — pipeline state machine. Public API:
  `startPreview`, `submitResponses`, `restore` (from localStorage on reload/Stripe return),
  `loadFromHistory` (by pipeline_id, for history actions), `reset`. Exposes
  `defaultSelectedCodes` state for pre-populating persona selection from history.
- `useBilling` (`hooks/useBilling.ts`) — `packs()`, `checkout(pack, quantity)`,
  `confirm(sessionId)`.
- `useCredits` (`hooks/useCredits.ts`) — polls `/user/status`, waits for auth to resolve.
- `PaywallDialog` — 3 pack cards (PLN only, no currency toggle), quantity input,
  redirects to Stripe.
- `HistoryDialog` — fetches `/history`, shows status chips + Resume/Resubmit buttons.
- `PreviewResults` — accepts optional `defaultSelectedCodes` prop to pre-select personas.

---

## What was done this session

- **Stripe payments** — full integration:
  - Backend: `PACKS` dict (PLN + Stripe Price IDs), `POST /billing/checkout` (uses
    `price:` not `price_data:`), `POST /webhook/stripe` (idempotent fulfillment),
    `POST /billing/confirm` (on-return fallback).
  - Frontend: `PaywallDialog` (PLN only, no USD toggle), `useBilling` hook, Stripe
    return handling in `App.tsx` (confirm → restore → auto-retry submit).
- **History resume + resubmit** — `HistoryDialog` now has action buttons; `usePipeline`
  gained `loadFromHistory` + `defaultSelectedCodes`; `PreviewResults` accepts
  `defaultSelectedCodes` prop; `GET /pipelines/{id}` extended with `form_title` and
  `selected_persona_codes`.

---

## What still needs to be done

### Prod auth config (manual — required before prod Google sign-in works)
Prod `authDomain` points at the custom domain; the OAuth handler must be authorized:
1. Firebase Console → Authentication → Settings → **Authorized domains**: ensure
   `forms-autofill.pchwala.dev` is listed.
2. Google Cloud → APIs & Services → Credentials → the Web OAuth client:
   add `https://forms-autofill.pchwala.dev` to **JS origins** and
   `https://forms-autofill.pchwala.dev/__/auth/handler` to **redirect URIs**.
3. Rebuild + `firebase deploy --only hosting`.

### Stripe webhook registration (required before payments work in prod)
- Stripe Dashboard → Developers → Webhooks → Add endpoint:
  - URL: `https://<your-backend>/webhook/stripe`
  - Event: `checkout.session.completed`
  - Copy the signing secret → `STRIPE_WEBHOOK_SECRET` in `backend/.env`
- For **local dev**: `stripe listen --forward-to localhost:8000/webhook/stripe`
  prints a local `whsec_...` to use as `STRIPE_WEBHOOK_SECRET`.

### Live testing (not exercisable offline)
- End-to-end run against a **real public Google Form** (extraction + submission are real
  network calls; requires a valid `OPENAI_API_KEY`).
- **Firestore credit transactions** (`consume_credits`/`add_credits`) against the real
  project — logic is straightforward but untested live.
- **Stripe test flow**: use card `4242 4242 4242 4242` through the full checkout →
  confirm credits granted → submit auto-retried.

### Smaller / known
- **Multi-process safety**: in-memory `_jobs` assumes a single uvicorn worker; a
  multi-worker deploy needs shared state (Redis/Firestore).
- Frontend bundle is >500 kB (single chunk) — code-splitting is a future nicety.

---

## Gotchas / things to know

- **`backend/.env` required vars**:
  ```
  OPENAI_API_KEY=sk-...
  FIREBASE_CREDENTIALS_JSON=./firebase_credentials.json
  CORS_ORIGINS=http://localhost:5173
  APP_URL=http://localhost:5173          # used for Stripe success/cancel redirect URLs
  STRIPE_SECRET_KEY=sk_test_...
  STRIPE_WEBHOOK_SECRET=whsec_...
  ```
- **Stripe Price IDs are test-mode IDs** — swap for live-mode IDs before going to prod.
  The `PACKS` dict in `backend/main.py` is the only place to change them.
- **`selected_persona_codes`** is set on a pipeline only after the first successful submit.
  For `preview_ready` pipelines, it's `null` in Firestore; `loadFromHistory` returns
  `null` → `PreviewResults` defaults to all personas checked.
- **Idempotent credit grants** — `credit_grants/{session_id}` prevents double-fulfillment
  from webhook retries + the on-return confirm call running simultaneously.
- Secrets: `backend/.env` and `backend/firebase_credentials.json` are both gitignored.
- Run the backend from the **repo root**: `uvicorn backend.main:app --reload`.
- Dev Firebase auth domain stays on `firebaseapp.com`; prod uses the custom domain
  `forms-autofill.pchwala.dev` — do not change the dev env var.
