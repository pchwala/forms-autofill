# Forms Autofill — Data Pipeline & API Reference

## Architecture Overview

```
┌─────────────────────────────────────┐
│  Frontend (React/Vite/TypeScript)   │
│  Firebase Auth (Google Sign-In)     │
└────────────────┬────────────────────┘
                 │ HTTP / SSE  (Bearer token)
                 ▼
┌─────────────────────────────────────┐
│  Backend (FastAPI / Python)         │
│  uvicorn, threading, asyncio        │
└──┬──────────┬──────────┬────────────┘
   │          │          │
   ▼          ▼          ▼
OpenAI     Google     Firebase
API        Forms      Admin SDK
```

---

## Pipeline Stages (5 Steps)

| Step | Name | Module | Description |
|------|------|--------|-------------|
| 1 | Extract form | `forms_extractor.py` | Fetches the public Google Form page, parses `FB_PUBLIC_LOAD_DATA_`, writes `data/form_config_N.json` |
| 2 | Generate strategy | `strategy_generator.py` | 3-stage GPT pipeline: web search → analysis → compile personas. Writes `research_basis_N.json`, `research_analysis_N.json`, `strategy_N.json` |
| 3 | Generate responses | `response_generator.py` | Calls OpenAI chat completions per persona to produce N response dicts |
| 4 | Shuffle responses | `orchestrator.py` | `random.shuffle()` on the response list to randomise submission order |
| 5 | Submit responses | `new_filler.py` | HTTP POST to Google Forms `formResponse` endpoint for each response dict |

### Step 2 — Strategy sub-steps

```
Step 2a: _step1_web_search()
  client.responses.create(model, tools=[web_search_preview])
  → data/research_basis_N.json

Step 2b: _step2_analyze()
  client.chat.completions.create(model, response_format=json_object)
  → data/research_analysis_N.json

Step 2c: _step3_compile()
  client.chat.completions.create(model, response_format=json_object)
  → data/strategy_N.json
```

---

## Backend API Endpoints

### `POST /run`
**Full pipeline — fire and forget**

Request body:
```json
{ "form_url": "https://docs.google.com/forms/...", "total_responses": 100, "model": "gpt-4.1" }
```
Response:
```json
{ "job_id": "<uuid>" }
```
- Spawns a daemon thread running all 5 steps sequentially
- Client streams events via `GET /stream/{job_id}`

---

### `POST /session`
**Step-by-step mode — create session**

Request body:
```json
{ "form_url": "...", "total_responses": 100, "model": "gpt-4.1" }
```
Response:
```json
{ "session_id": "<uuid>" }
```

---

### `GET /session/{session_id}`
**Get current session state**

Response:
```json
{ "session_id": "...", "current_step": 2, "status": "idle", "total_steps": 5 }
```
`status` values: `idle` | `running` | `done` | `error`

---

### `POST /session/{session_id}/advance`
**Execute the next pipeline step**

Response:
```json
{ "job_id": "<uuid>", "step": 1 }
```
- Returns `409` if a step is already running or the pipeline is complete
- Client streams step events via `GET /stream/{job_id}`

---

### `GET /stream/{job_id}`
**Server-Sent Events (SSE) stream**

`Content-Type: text/event-stream`

| Event `type` | Additional fields | Meaning |
|---|---|---|
| `step` | `step` (1–5), `status` (`start`/`done`), `message` | Step lifecycle notification |
| `step_complete` | `step` | Step-by-step mode: step finished, awaiting user action |
| `done` | `total` | Full pipeline completed successfully |
| `error` | `message` | Pipeline error — stream closes |

---

## Frontend → Backend Call Flows

### Full pipeline mode (`mode = "full"`)

```
User clicks Start
  → POST /run  { form_url, total_responses, model }
  ← { job_id }
  → GET /stream/{job_id}   (fetch-based SSE, Authorization: Bearer <token>)
    ← data: { type: "step", step: 1, status: "start", message: "Extracting form..." }
    ← data: { type: "step", step: 1, status: "done",  message: "Form extracted: ..." }
    ← data: { type: "step", step: 2, status: "start", message: "Generating strategy..." }
    ...
    ← data: { type: "step", step: 5, status: "done",  message: "All responses submitted" }
    ← data: { type: "done", total: 100 }
```

### Step-by-step mode (`mode = "step"`)

```
User clicks Start
  → POST /session  { form_url, total_responses, model }
  ← { session_id }
  → POST /session/{session_id}/advance
  ← { job_id, step: 1 }
  → GET /stream/{job_id}
    ← data: { type: "step", step: 1, status: "start" }
    ← data: { type: "step", step: 1, status: "done" }
    ← data: { type: "step_complete", step: 1 }
  [frontend sets status = "paused", user reviews output]

  User clicks Next Step
  → POST /session/{session_id}/advance
  ← { job_id, step: 2 }
  → GET /stream/{job_id}
    ... (repeat for steps 2–5)
    ← data: { type: "done", total: 100 }
```

---

## Authentication

| Layer | Mechanism |
|-------|-----------|
| Frontend | Firebase Auth with Google provider (`signInWithPopup`) |
| Token retrieval | `user.getIdToken()` via `useAuth` hook |
| Transport | `Authorization: Bearer <token>` header on every request |
| Backend verification | `firebase_admin.auth.verify_id_token()` in `_verify()` |
| Bypass (dev only) | `AUTH_DISABLED=true` (backend) / `VITE_AUTH_DISABLED=true` (frontend) |

> **SSE note:** Native `EventSource` does not support custom headers.
> The frontend uses `fetch()` to open the SSE response body as a `ReadableStream`,
> allowing the `Authorization` header to be sent normally.

---

## Data Files

| File | Produced by | Consumed by |
|------|-------------|-------------|
| `data/form_config_N.json` | `forms_extractor.extract()` | `strategy_generator`, `response_generator`, `new_filler` |
| `data/research_basis_N.json` | strategy step 2a (web search) | strategy step 2b (analysis) |
| `data/research_analysis_N.json` | strategy step 2b (analysis) | strategy step 2c (compile) |
| `data/strategy_N.json` | strategy step 2c (compile) | `ResponseGenerator` (step 3) |

`N` is an auto-incrementing integer derived from existing files in `data/`.

---

## Environment Variables

### Backend

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENAI_API_KEY` | *(required)* | OpenAI API key for all GPT calls |
| `FIREBASE_CREDENTIALS_JSON` | *(optional)* | Firebase service account JSON; falls back to Application Default Credentials |
| `AUTH_DISABLED` | `false` | Set `true` to skip token verification (dev only) |
| `CORS_ORIGINS` | `*` | Comma-separated list of allowed CORS origins |

### Frontend (`VITE_*`)

| Variable | Purpose |
|----------|---------|
| `VITE_API_URL` | Backend base URL (default: `http://localhost:8000`) |
| `VITE_AUTH_DISABLED` | Set `true` to skip Firebase auth (dev only) |
| `VITE_FIREBASE_API_KEY` | Firebase web API key |
| `VITE_FIREBASE_AUTH_DOMAIN` | Firebase auth domain |
| `VITE_FIREBASE_PROJECT_ID` | Firebase project ID |
| `VITE_FIREBASE_APP_ID` | Firebase app ID |
