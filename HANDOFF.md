# Handoff — Anonymous Access + Preview/Paywall Refactor

_Last updated: 2026-06-13. Branch: `feature`._

This document captures the state of the in-progress pivot from a sign-in-gated,
single-shot pipeline to an **anonymous, preview-then-pay** product. Read this first.

---

## The product model (what we're building)

1. **Anonymous access** — anyone can use the site without registering (Firebase
   Anonymous Auth; upgradeable to Google later via `linkWithPopup`).
2. **Free preview** — running a form does steps 1–2 only (extract → strategy). The
   user sees the generated **personas** (checkboxes to include/exclude) and the
   **predicted answer distributions** for the first ≤10 option-based questions.
   This is computed *from the strategy JSON* — no paid generation call.
3. **Desired-outcome prompt** — optional free-text field; injected into strategy
   generation so it skews the personas/distributions the user reviews (outranks the
   research-based defaults).
4. **Paywall (credits)** — generating + submitting the real responses (steps 3–5)
   consumes **1 credit**. Payment is a **placeholder** right now (a button that grants
   credits); Stripe comes later.

### Locked decisions
- Gating = **credits counter** (1 credit = 1 submit run). `CREDITS_PER_PURCHASE` env
  controls grant size; the single-vs-N-pack pricing decision is deferred.
- Unchecking personas **renormalizes** the selected personas' `count_percent` to 100%
  (total response count stays N).
- Preview shows the **first ≤10 questions that have options**; free-text skipped.

---

## What was done this session

### Earlier cleanups (committed)
- Added `CLAUDE.md`.
- Fixed `backend/shuffle.py` — wrapped its CLI body in `if __name__ == "__main__"`
  (module-level code was running on import and crashing uvicorn / the debugger).
- Removed **Ko-fi** entirely (backend webhook + `mark_paid` + frontend links).
- Removed the **step-by-step mode** from the frontend (backend `/session*` endpoints
  left intact but unused).

### The refactor (committed)
**Backend**
- `firestore_service.py` — credits model: `get_credits`, `add_credits` (transactional),
  `consume_credit` (transactional decrement, returns `False` at 0). `get_or_create_user`
  seeds `credits: 0` and tolerates empty email (anon). `create_pipeline` stores
  `desire_prompt`/`preview`/`selected_persona_codes`; added `update_pipeline`.
- `strategy_generator.py` — optional `desire_prompt` threaded through; prepends a
  high-priority `USER DIRECTIVE` block to the step-2 analysis and step-3 compile prompts.
- `preview.py` (NEW) — `select_preview_questions`, `persona_answer_weights`,
  `aggregate_distributions`, `compute_preview`, `filter_and_renormalize_personas`.
- `main.py` — `POST /preview` (free; extract+strategy, returns `{job_id, pipeline_id}`,
  emits a `preview` SSE result), `POST /pipelines/{id}/submit` (consumes a credit → **402**
  if none; generates+shuffles+submits selected personas; **refunds** the credit on
  failure), `GET /user/status` → `{credits}`, `POST /credits/grant` (placeholder paywall).
  In-memory `_pipelines` dict bridges preview→submit. Legacy `/run` + `/session*` kept
  but de-gated.
- `orchestrator.py` — `step2_strategy` now accepts/forwards `desire_prompt`.

**Frontend**
- `hooks/useAuth.ts` — `signInAnonymously` on mount; `signInWithGoogle` upgrades anon via
  `linkWithPopup`; exposes `isAnonymous`. (Now also tolerates anon-sign-in failure instead
  of hanging — see below.)
- `components/AuthGuard.tsx` — no longer blocks; just a loading spinner until auth resolves.
- `components/layout/Navbar.tsx` — shows credits + "Sign in" for guests, user menu for
  Google accounts.
- `hooks/usePipeline.ts` — `'preview'`/`'submitting'` states; `startPreview` +
  `submitResponses` (402 → `'blocked'`). Session/advance paths removed.
- `hooks/useCredits.ts` (NEW, replaces `useUserStatus.ts`).
- `components/PreviewResults.tsx` (NEW) — persona checkboxes + live-recomputed bar charts.
- `utils/distributions.ts` (NEW) — `aggregateDistributions`, mirrors `backend/preview.py`.
- `components/PaywallDialog.tsx` (NEW) — placeholder Pay button → `POST /credits/grant`.
- `components/InputForm.tsx` — added "Desired outcome" textarea; `onStart(url,count,prompt)`.
- `components/sections/{PipelineSection,HowItWorksSection}.tsx` — rewired for the new flow.
- `App.tsx` — orchestrates preview → (credits ? submit : paywall) → submit.

### Bug fixes
- `main.py:_load_firebase_credentials` — resolves a **relative** `FIREBASE_CREDENTIALS_JSON`
  against the `backend/` package dir (uvicorn runs from repo root, so `./firebase_credentials.json`
  wasn't found). _(committed: b3e7899)_
- `backend/.env` — `CORS_ORIGINS` had `http://localhost:8000` (the backend itself) instead of
  the Vite dev origin; changed to `http://localhost:5173`. _(gitignored file, not committed)_
- `hooks/useAuth.ts` — catches a failed `signInAnonymously` and stops loading so the app
  renders instead of an infinite spinner. _(**uncommitted** — only dirty file right now)_

### Verification done
- Backend compiles; app boots; routes present; `/user/status` + `/credits/grant` return
  correct shapes; `/preview` starts a job and SSE streams step/error events.
- **Offline full-pipeline test** (stubbing only the form-extraction and Google-submission
  network boundaries): preview → 3 personas + 6 option-based questions (free-text skipped);
  submit with a persona subset renormalized correctly (e.g. A+C → 14+6 = 20).
- `npm run build` passes; `tsc` clean for all touched files (one pre-existing exception, below).

---

## What still needs to be done

### Blocking — must happen before the flow works live
1. **Enable Anonymous sign-in in the Firebase console** (project `forms-autofill-fc6aa`):
   Authentication → Sign-in method → add **Anonymous** → enable. Without it,
   `signInAnonymously` fails with `auth/admin-restricted-operation` and the whole auth
   chain 401s. _(This is the current top error.)_
2. **Restart the backend** after the `CORS_ORIGINS` change.
3. **Commit** the dirty `frontend/src/hooks/useAuth.ts`.

### Live testing not yet possible in this environment
4. End-to-end run against a **real public Google Form** (extraction + submission are real
   network calls, not stubbed).
5. **Firestore credit transactions** (`consume_credit`/`add_credits`) against the real
   project — logic is straightforward but untested live.

### Real payment integration
6. **Stripe**: replace `POST /credits/grant` (placeholder) with Stripe Checkout session
   creation + a webhook that calls `add_credits`. Decide `CREDITS_PER_PURCHASE` / pricing
   (single submission vs N-pack).
7. **Stripe redirect resume**: `_pipelines` is **in-memory**, fine for the dialog-based
   placeholder (process stays up). Stripe redirects away and may span a server restart, so
   the submit step must resume from **Firestore** (`step_form_config`/`step_strategy`/
   `selected_persona_codes` are already persisted) rather than `_pipelines`.

### Cleanup / smaller items
8. **History resubmit** is currently degraded — `HistoryDialog.onSelect` is a no-op (just
   closes). Decide whether to restore resubmit-from-history and gate it behind a credit.
9. **Legacy endpoints** `/run`, `/session*`, `/resubmit*` are unused; remove once the new
   flow is confirmed.
10. **Pre-existing tsc error** in `frontend/src/components/PipelineProgress.tsx:93`
    (`StepIconComponent` not on `StepLabelProps`). Untouched this session; the project builds
    via esbuild which skips type-checking. Worth a proper fix (use the `slots`/`slotProps`
    API or cast).
11. **Multi-process safety**: in-memory `_jobs`/`_sessions`/`_pipelines` assume a single
    uvicorn worker. A multi-worker deploy needs shared state (Firestore/Redis).

---

## Gotchas / things to know
- **Dev mode** (`AUTH_DISABLED=true` + `VITE_AUTH_DISABLED=true`): `/user/status` and
  `/credits/grant` return `credits: 999999`, submit never charges, no Firestore. The
  preview math + orchestration are exercisable, but **form extraction, AI calls, and Google
  submission all hit the network** (a valid `OPENAI_API_KEY` is required).
- The **desire prompt** affects the preview because it's injected at strategy time (step 2);
  generation then samples from the already-skewed personas, so submissions stay faithful.
- Secrets: `backend/.env` (live `OPENAI_API_KEY`) and `backend/firebase_credentials.json`
  are both gitignored. Keep them out of commits.
