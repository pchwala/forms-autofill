# Handoff — Anonymous Access + Preview/Paywall Product

_Last updated: 2026-06-13. Branch: `feature`. Latest commit: `2f294d2`._

State of the pivot from a sign-in-gated, single-shot pipeline to an **anonymous,
preview-then-pay** product. The pivot and a cleanup pass are done; the main remaining
feature is **Stripe payments**. Read this first.

---

## The product model (what we're building)

1. **Anonymous access** — anyone can use the site without registering (Firebase
   Anonymous Auth; upgradeable to Google via `linkWithPopup`).
2. **Free preview** — running a form does steps 1–2 only (extract → strategy). The
   user sees the generated **personas** (checkboxes to include/exclude) and the
   **predicted answer distributions** for the first ≤10 option-based questions —
   computed *from the strategy JSON*, no paid generation call.
3. **Desired-outcome prompt** — optional free-text field; injected into strategy
   generation so it skews the personas/distributions the user reviews (outranks the
   research-based defaults).
4. **Paywall (credits)** — generating + submitting the real responses (steps 3–5)
   consumes **1 credit**. Payment is still a **placeholder** (`POST /credits/grant`
   grants credits with no real charge); Stripe is the next feature.

### Locked decisions
- Gating = **credits counter** (1 credit = 1 submit run). `CREDITS_PER_PURCHASE` env
  controls grant size; single-vs-N-pack pricing is deferred.
- Unchecking personas **renormalizes** the selected personas' `count_percent` to 100%
  (total response count stays N).
- Preview shows the **first ≤10 questions that have options**; free-text skipped.
- **History is view-only** (read-only list of past runs). Resubmit-from-history was
  intentionally dropped; if it returns it must be a proper credit-gated feature.

---

## Current backend shape (`backend/main.py`)

Only six routes remain after the cleanup pass — all legacy endpoints were removed:
- `POST /preview` — free; extract+strategy, returns `{job_id, pipeline_id}`, emits a
  `preview` SSE result. No credit consumed.
- `POST /pipelines/{id}/submit` — consumes a credit (**402** if none), generates +
  shuffles + submits the selected personas, **refunds** the credit on failure.
- `GET /user/status` → `{credits}`. `POST /credits/grant` — placeholder paywall.
- `GET /stream/{job_id}` — SSE drain. `GET /history` — read-only list.

In-memory `_pipelines` dict bridges preview→submit; `_jobs` holds SSE queues.
Firestore (`firestore_service.py`) persists `users/{uid}` (credits) and
`pipelines/{pipeline_id}` (`step_form_config`/`step_strategy`/`step_responses`/
`selected_persona_codes`, etc.). `get_pipeline` is kept for the upcoming Stripe resume.

---

## What was done this session

All committed on `feature`:

- **Auth 401 fixed** — Anonymous sign-in was disabled in the Firebase console (now
  enabled by the user). Also fixed a guaranteed cold-load 401: `useCredits` now takes
  `(getToken, user, authLoading)` and waits for auth to resolve before calling
  `/user/status` (`useCredits.ts`, `App.tsx`).
- **Double Google popup fixed** (`useAuth.ts`) — on `auth/credential-already-in-use`,
  reuse the credential via `signInWithCredential` instead of opening a second popup.
- **Storage-partitioning prod fix** (`67a18da`) — prod `VITE_FIREBASE_AUTH_DOMAIN` now
  points at the app's own custom domain `forms-autofill.pchwala.dev` (served by Firebase
  Hosting at `/__/auth/`), making the auth iframe first-party. **Dev stays on
  `firebaseapp.com`** — the custom-domain handler would break popup on localhost.
- **favicon** — added `frontend/public/favicon.svg` + `<link rel="icon">`.
- **Cleanup pass** (`2f294d2`):
  - Removed all legacy endpoints (`/run`, `/session*`, `/result`, `/resubmit*`,
    `/history/{id}`, `/history/{id}/resubmit`) + their request models, the `_sessions`
    dict, and `run_pipeline`.
  - Removed the **AI stub harness** (`backend/stub.py`, all `AI_SWITCH_STUB` wiring).
  - Made **History view-only** (`HistoryDialog.tsx`, `App.tsx`).
  - Fixed the MUI v9 `PipelineProgress.tsx` type error (`StepIconComponent` →
    `slots={{ stepIcon }}`).

Verified: backend imports clean, routes are exactly the six above, `tsc --noEmit` clean,
`npm run build` passes.

---

## What still needs to be done

### Prod auth config (manual — required before prod Google sign-in works)
Because prod `authDomain` is now the custom domain, the OAuth handler must be authorized
or sign-in fails with `redirect_uri_mismatch`:
1. Firebase Console → Authentication → Settings → **Authorized domains**: ensure
   `forms-autofill.pchwala.dev` is listed.
2. Google Cloud → APIs & Services → Credentials → the Web OAuth client:
   add `https://forms-autofill.pchwala.dev` to **JS origins** and
   `https://forms-autofill.pchwala.dev/__/auth/handler` to **redirect URIs**.
3. Rebuild + `firebase deploy --only hosting`.

### Stripe payments (the main remaining feature)
- Replace `POST /credits/grant` (placeholder) with Stripe Checkout session creation +
  a webhook that calls `add_credits`. Decide `CREDITS_PER_PURCHASE` / pricing.
- **Resume across the Stripe redirect**: `_pipelines` is in-memory; Stripe redirects away
  and may span a server restart, so submit must resume from **Firestore** (the step data
  + `selected_persona_codes` are already persisted; `get_pipeline` reads them) rather than
  relying on `_pipelines`.

### Live testing (not exercisable offline)
- End-to-end run against a **real public Google Form** (extraction + submission are real
  network calls). The AI stub is gone, so this also spends real OpenAI tokens.
- **Firestore credit transactions** (`consume_credit`/`add_credits`) against the real
  project — logic is straightforward but untested live.

### Smaller / known
- **Multi-process safety**: in-memory `_jobs`/`_pipelines` assume a single uvicorn worker;
  a multi-worker deploy needs shared state (Firestore/Redis).
- Frontend bundle is >500 kB (single chunk) — code-splitting is a future nicety.

---

## Gotchas / things to know
- **Dev mode** (`AUTH_DISABLED=true` + `VITE_AUTH_DISABLED=true`): `/user/status` and
  `/credits/grant` return `credits: 999999`, submit never charges, no Firestore. Preview
  math + orchestration are exercisable, but **form extraction, AI calls, and Google
  submission all hit the network** (a valid `OPENAI_API_KEY` is required — the stub that
  used to avoid this is gone).
- The **desire prompt** affects the preview because it's injected at strategy time (step 2);
  generation then samples from the already-skewed personas, so submissions stay faithful.
- Secrets: `backend/.env` (live `OPENAI_API_KEY`) and `backend/firebase_credentials.json`
  are both gitignored. Keep them out of commits.
- Run the backend from the **repo root** as a package: `uvicorn backend.main:app --reload`.
