# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend

```bash
# Run the backend (from project root — backend is a package)
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000

# Interactive API docs
# http://localhost:8000/docs

# Run strategy generator standalone (CLI)
python -m backend.strategy_generator data/form_config_1.json
python -m backend.strategy_generator data/form_config_1.json --step 2  # resume from step 2
```

### Frontend

```bash
cd frontend
npm run dev      # dev server at http://localhost:5173
npm run build    # production build → dist/
npm run preview  # serve the dist/ build locally
```

### Docker (backend only)

```bash
docker build -t forms-autofill-backend ./backend
docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... \
  -e FIREBASE_CREDENTIALS_JSON="$(cat backend/firebase_credentials.json)" forms-autofill-backend
```

## Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Notes |
|---|---|---|
| `OPENAI_API_KEY` | — | Required for AI pipeline steps |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated |
| `FIREBASE_CREDENTIALS_JSON` | — | File path or raw JSON; required (auth is always enabled) |

### Frontend (`frontend/.env.development`)

| Variable | Notes |
|---|---|
| `VITE_API_URL` | Backend URL, defaults to `http://localhost:8000` |
| `VITE_FIREBASE_*` | Firebase config (required — auth is always enabled) |

## Architecture

### Backend (`backend/`)

FastAPI app (`main.py`) that exposes two pipeline execution modes:

- **Full pipeline** (`POST /run`): kicks off all 5 steps in one background thread; returns a `job_id`.
- **Session mode** (`POST /session` + `POST /session/{id}/advance`): step-by-step execution where the client advances one step at a time.

Both modes emit progress events into an `asyncio.Queue`, which are drained by a Server-Sent Events endpoint (`GET /stream/{job_id}`).

In-memory state (`_jobs`, `_sessions`) is not persisted across restarts.

**Pipeline steps** (in `orchestrator.py`):

1. `step1_extract` — fetches the Google Form's internal JSON payload via `requests` and parses it into `data/{base}_form_config.json` (`forms_extractor.py`).
2. `step2_strategy` — 3-call GPT-4.1 pipeline: web search → analysis → compile personas → `data/{base}_strategy.json` (`strategy_generator.py`).
3. `step3_generate` — generates up to 200 AI responses using persona-weighted answers (`response_generator.py`).
4. `step4_shuffle` — `random.shuffle` in memory.
5. `step5_submit` — posts each response set to the Google Form via `requests` (`new_filler.py`). Loops in batches if `total_responses > len(generated)`.

**Auth** (`_verify` in `main.py`): verifies Firebase ID tokens from `Authorization: Bearer <token>`. Auth is always enabled (including local dev), so the backend requires `FIREBASE_CREDENTIALS_JSON` to start.

**Payment gating** (`firestore_service.py`): each user gets one free pipeline run (`free_used` flag). Paid users (`paid=true`) are unlocked via a Ko-fi webhook (`POST /webhook/kofi`).

**Firestore collections**: `users/{uid}`, `pipelines/{pipeline_id}` (stores per-step JSON output as `step_form_config`, `step_strategy`, `step_responses`, etc.).

### Frontend (`frontend/src/`)

Single-page React 19 app with Material UI (dark theme).

**State management** — no external store; all pipeline state lives in the `usePipeline` hook (`hooks/usePipeline.ts`):
- `status`: `idle | running | paused | done | error | blocked`
- `steps`: array of `{ label, status }` for the stepper UI
- Parses SSE events from `GET /stream/{jobId}` using a `fetch` + `ReadableStream` pattern (not the native `EventSource` API, because `EventSource` doesn't support custom headers).

**Auth** — `useAuth` hook (`hooks/useAuth.ts`) wraps Firebase Auth: every visitor gets an anonymous session (upgradeable to Google via `linkWithPopup`), and `AuthGuard` shows a spinner until the session resolves. Requires the `VITE_FIREBASE_*` config.

**Key components**:
- `PipelineSection` — the main control panel; receives all pipeline state and handlers as props from `App.tsx`.
- `InputForm` — form URL + response count input; chooses between `full` and `step-by-step` (`PipelineMode`).
- `PipelineProgress` — stepper + log + submit progress bar.
- `HistoryDialog` — lists past pipeline runs from `GET /history`; lets the user resubmit a completed pipeline by its `pipeline_id`.

**Resubmit flow**: after a successful run, the user can resubmit (shuffle + re-submit only) without regenerating AI responses. The hook prefers `POST /session/{id}/resubmit` if a live session exists, otherwise `POST /resubmit` with the `result_id`, or `POST /history/{pipelineId}/resubmit` for historical runs.
