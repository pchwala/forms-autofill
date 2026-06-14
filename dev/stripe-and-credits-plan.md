# Plan — Stripe Payments + Per-Response Credit Model

> Status: **Part A ✅ implemented**, **Part C ✅ implemented**, **Part B (Stripe) ⬜ remaining**.
> Branch: `feature`. This is the working spec; see "Critical files" + "Verification" at the end.

## Context

The app pivoted to an anonymous, **preview-then-pay** product. Free preview = steps 1–2
(extract → strategy); paid submit = steps 3–5 (generate → shuffle → submit). Payment is
currently a **placeholder** (`POST /credits/grant` grants credits with no charge).

This change does two things:

1. **Connect Stripe** so users actually buy credits (USD or PLN, three packs).
2. **Fix the credit model.** Previously `consume_credit` charged **1 credit per submit *run*** and
   refunded 1 on total failure. The intended model is **1 credit = 1 submitted response**,
   **deducted after submission**, charging only for responses that actually confirmed.

Confirmed product decisions:
- **Charge successful only** — deduct credits = responses that actually submitted; pre-check
  that balance ≥ requested `total_responses` before starting (402 otherwise).
- **Quantity per checkout** — one Stripe Checkout can buy N of a chosen pack.
- Prod auth config is already done and working; anonymous users upgrade to Google **or**
  email+password (auth itself is out of scope here).
- Dev mode (`AUTH_DISABLED`) is no longer used — we always run with auth enabled. Its remaining
  in-memory fallback (`_dev_pipelines`) is kept minimal and slated for removal.

### Credit packs (single source of truth in backend; minor units)

| Pack | Credits | USD | PLN |
|---|---|---|---|
| Small | 10 | $0.99 (`usd: 99`) | 4.99 zł (`pln: 499`) |
| Medium | 50 | $4.25 (`usd: 425`) — 15% off | 21.25 zł (`pln: 2125`) |
| Large | 100 | $7.50 (`usd: 750`) — 25% off | 37.50 zł (`pln: 3750`) |

---

## Part A — Per-response credit model ✅ IMPLEMENTED

Done on `feature`:
- `backend/firestore_service.py` — `consume_credit(uid)` → `consume_credits(uid, n) -> int`
  (atomic deduct `min(current, n)`, returns amount deducted). `add_credits(uid, n,
  idempotency_key=None)` records `credit_grants/{key}` in-transaction so a repeated grant is a
  no-op (guards Stripe webhook + confirm double-fulfillment).
- `backend/new_filler.py` — `submit_range(...)` tallies and returns the confirmed count.
- `backend/orchestrator.py` — `step5_submit(...)` sums batches and returns total confirmed.
- `backend/main.py` `POST /pipelines/{id}/submit` — pre-checks `get_credits(uid) >=
  total_responses` (**402** if short); persona-validation failure → **400** (nothing consumed);
  worker charges `consume_credits(uid, succeeded)` after the run; **no charge / no refund on
  failure**. SSE `done.total` is the confirmed count.

---

## Part B — Stripe integration ⬜ REMAINING

### Backend
- **Add dependency** `stripe` to `backend/requirements.txt`; `import stripe` and set
  `stripe.api_key = STRIPE_SECRET_KEY` at startup in `main.py`.
- **New env vars** (`backend/.env` + `.env.example`): `STRIPE_SECRET_KEY`,
  `STRIPE_WEBHOOK_SECRET`, `APP_URL` (for success/cancel redirects; default the first
  `CORS_ORIGINS` entry). Frontend needs **no** Stripe key — we use hosted Checkout redirect.
- **`PACKS` dict** in `main.py` (or a small `billing.py`) per the table above.

New routes:
- `GET /billing/packs` → returns `PACKS` (credits + per-currency prices) so the UI has one
  source of truth.
- `POST /billing/checkout` (auth) — body `{pack: "10"|"50"|"100", currency: "usd"|"pln",
  quantity: int}`. Creates a Stripe Checkout Session: `mode="payment"`, one line item via
  inline `price_data` (`currency`, `unit_amount` from `PACKS`, `product_data.name` e.g.
  `"100 credits"`), `quantity`, `metadata={uid, credits: pack.credits * quantity}`,
  `success_url=f"{APP_URL}/?checkout=success&session_id={{CHECKOUT_SESSION_ID}}"`,
  `cancel_url=f"{APP_URL}/?checkout=cancel"`. Return `{url}`.
- `POST /webhook/stripe` — read raw body, verify signature with `STRIPE_WEBHOOK_SECRET` via
  `stripe.Webhook.construct_event`. On `checkout.session.completed` call the shared
  `fulfill_checkout(session)`.
- `POST /billing/confirm` (auth) — body `{session_id}`. Retrieve the session from Stripe; if
  `payment_status == "paid"` call `fulfill_checkout(session)`. Return `{credits}`. **This is the
  on-return fallback** so fulfillment doesn't depend on webhook timing.

Shared `fulfill_checkout(session)`: grant `session.metadata["credits"]` to
`session.metadata["uid"]` via `add_credits(uid, credits, idempotency_key=session.id)` — both
the webhook and confirm call it, idempotency makes the double-call safe.

- **Repurpose `POST /credits/grant`:** keep only the `AUTH_DISABLED` branch (returns `999999`
  for dev); remove the real-money placeholder grant.

### Frontend
- **No new npm dependency** — redirect to hosted Checkout via `window.location.href`.
- `frontend/src/hooks/useBilling.ts` (new, small): `packs()` (GET /billing/packs),
  `checkout(pack, currency, quantity)` → returns `{url}`, `confirm(sessionId)`. Reuses the
  `getToken()` + `Authorization: Bearer` + `VITE_API_URL` pattern from `useCredits.ts`.
- `frontend/src/components/PaywallDialog.tsx` — replace the single "Pay (placeholder)" button
  with: 3 pack cards, a **USD/PLN** toggle, a **quantity** input, and a "you need X / have Y"
  line. On confirm: the Part-C `localStorage` intent is already saved (selected personas merged
  in at submit time), then `window.location.href = checkoutUrl`.
- `frontend/src/App.tsx` — on mount, detect `?checkout=success&session_id=...`: call
  `confirm(sessionId)`, `refreshCredits()`, then use the Part-C localStorage intent +
  `GET /pipelines/{id}` (already restored by `usePipeline.restore()`) to **auto-retry submit**
  if credits now suffice; strip the query params from the URL. `?checkout=cancel` just clears
  params and reopens the paywall. (No backend resume work — Part C made submit store-backed.)
- `frontend/src/components/PreviewResults.tsx` — button copy reflects cost, e.g.
  `Generate & submit {count} responses ({count} credits)`; surface balance vs. needed.

---

## Part C — Remove in-memory `_pipelines`; make Firestore the source of truth ✅ IMPLEMENTED

**Why this mattered.** `_pipelines` was an **in-memory** dict that was the *authoritative*
submit state (`config_path`/`strategy_path`, `base_name`, `fs_id`, `status`). It was lost on
restart / multi-worker, and the Stripe redirect drives the browser away and back — so a
"rehydrate from Firestore only if the dict is missing" approach would have been a fragile
workaround. With money involved, the pipeline record must be **persisted state**, not process
memory. This refactor removed `_pipelines` as a source of truth so submit always runs from the
persisted record, and the Stripe redirect "just works" with no special resume code.

**Key enabler:** the generation/submission code was already dict-based — `ResponseGenerator`/
`FormFiller` are built from a config **dict**, and `step3_generate`/`step5_submit` only read the
config file to reproduce that dict. Everything submit needs (`step_form_config`, `step_strategy`,
`base_name`) is already persisted to Firestore at preview time.

### Backend — full dict-based, Firestore-authoritative (done)

1. **Unified the id.** Dropped the `pipeline_id` (in-memory key) vs `fs_id` (Firestore doc id)
   duality. `/preview` mints one uuid and returns it; `create_pipeline(pipeline_id, uid, ...)`
   takes an explicit id so the Firestore doc id == the id the client holds. Internally
   `fs_id = pipeline_id if not AUTH_DISABLED else None` keeps Firestore writes prod-only.

2. **Generation takes dicts** (no config/strategy scratch files in submit):
   - `step3_generate(form_config: dict, strategy: dict, total_responses, emit, pipeline_id=None)`.
   - `step5_submit(form_config: dict, responses, total_responses, emit) -> int`.
   - `ResponseGenerator.generate(self, output_file=None, emit=None, strategy: dict | None = None)`
     — uses the passed `strategy` dict; falls back to `config["strategy_file"]` for the CLI.

3. **Removed `_pipelines`.** Added `_load_pipeline_record(pipeline_id, uid) -> dict | None`
   returning `{uid, base_name, form_config, strategy, preview, status}`:
   - **Prod:** `get_pipeline(pipeline_id, uid)` (filters by `user_uid`) → maps
     `step_form_config`/`step_strategy`/`base_name`/`user_uid`/`status`. Returns `None` (→404)
     if missing, not owned, or `form_config`/`strategy` not yet persisted.
   - **Dev (`AUTH_DISABLED` only — minimal, slated for removal):** a module-level
     `_dev_pipelines` written by `/preview`. No sidecar files.

4. **`/preview`** persists the record (prod: `create_pipeline`+`save_pipeline_step`+
   `update_pipeline`; dev: `_dev_pipelines`) and emits `done` with the unified `pipeline_id`.
   Error path sets status via `fail_pipeline` / drops the dev entry.

5. **`/pipelines/{id}/submit`** loads via `_load_pipeline_record`, runs the Part-A credit flow,
   and feeds `record["form_config"]` + `filter_and_renormalize_personas(record["strategy"],
   codes)` straight into the dict-based steps. Resubmittable on failure; blocked only while
   `in_progress`.

6. **`GET /pipelines/{id}`** (new) → `{status, preview, total_responses}` so the frontend can
   restore the preview after a reload/redirect (prod: `get_pipeline`; dev: `_dev_pipelines`).

7. **`_jobs` stays in-memory by design** — transient SSE progress for a live run only; a dead
   process means a dead run, and credits charge after submission, so no money rides on it.
   Documented in `main.py`.

### Frontend — localStorage holds intent, backend holds the data (done)

- `usePipeline.ts` — a `forms-autofill:pending` localStorage layer (`{pipelineId, count,
  selectedCodes?}`): saved when preview is ready, `selectedCodes` merged in before submit,
  cleared on done/reset. New `restore()` action fetches `GET /pipelines/{id}`, repopulates
  `preview`/`steps`/`status` (no re-run), and returns the stored intent.
- `App.tsx` — a guarded effect calls `restore()` once auth resolves and rehydrates `count`.
- This is the mechanism Part B's Stripe return reuses (fetch credits → restore preview →
  auto-submit stored codes); **no backend resume code is needed**.

---

## Critical files

- **Part A (done):** `backend/firestore_service.py` (`consume_credits`, `add_credits`
  idempotency), `backend/new_filler.py` + `backend/orchestrator.py` (`step5_submit` returns
  count), `backend/main.py` (submit credit flow).
- **Part C (done):** `backend/main.py` — dropped `_pipelines`, added `_dev_pipelines`,
  `_load_pipeline_record`, id unification, `GET /pipelines/{id}`, `/preview` + submit rewrites.
  `backend/orchestrator.py` (`step3_generate`/`step5_submit` take dicts),
  `backend/response_generator.py` (`generate(strategy=...)`),
  `backend/firestore_service.py` (`create_pipeline` accepts explicit id).
  `frontend/src/hooks/usePipeline.ts` + `App.tsx` (localStorage intent + `GET /pipelines/{id}`
  restore).
- **Part B (Stripe, remaining):** `backend/main.py` (`/billing/*`, `/webhook/stripe`,
  `fulfill_checkout`, `PACKS`, Stripe init, repurposed `/credits/grant`),
  `backend/requirements.txt`, `backend/.env(.example)`, `frontend/src/hooks/useBilling.ts` (new),
  `components/PaywallDialog.tsx`, `App.tsx`, `components/PreviewResults.tsx`, `hooks/useCredits.ts`.

## Verification

1. **Static:** `AUTH_DISABLED=true python -c "import backend.main"` clean (routes correct);
   `cd frontend && npm run build` clean. (No standalone `tsc` is installed — the build is
   `vite build`/esbuild.)
2. **Part C — no in-memory source of truth (live, AUTH_ENABLED):** run preview→submit
   end-to-end against a real public Google Form so submit pulls `step_form_config`/
   `step_strategy` from Firestore; confirm the dict-based steps run with no config/strategy
   files written under `data/`. Then **restart the backend between preview and submit** and
   confirm submit still works (proves Firestore is authoritative). `GET /pipelines/{id}` after
   a reload restores the preview.
3. **Per-response charge (live):** with N credits, submit a run of M responses; confirm balance
   drops by the number actually confirmed (not by 1, not by M-on-failure).
4. **Stripe (test mode):** set test keys; `stripe listen --forward-to
   localhost:8000/webhook/stripe`; submit that 402s → paywall (pick pack/currency/qty) →
   checkout → pay with `4242 4242 4242 4242` → return to `?checkout=success` → credits granted
   **once** (replay the webhook / re-call `/billing/confirm` to prove idempotency) → preview
   restored from `GET /pipelines/{id}` → submit auto-retries.
5. **Redirect durability:** start a checkout, **kill the backend while on Stripe's page**,
   restart, return to the app → submit completes (it reads the pipeline from Firestore, not
   memory).
