# Plan: Firestore Pipeline Persistence + Title-Based File Naming

## TL;DR
Save each step's JSON output to Firestore under a `pipelines` collection, enabling history + resubmission across sessions. Also change local file naming from sequential numeric (`form_config_1.json`) to first-24-chars-of-form-title based slugs, with `_2` etc. on collision.

---

## Phase 1: Title-Based File Naming Convention

1. `forms_extractor.py` - Add `_slugify(title, max_len=24)`: lowercase, spaces->underscores, strip non-alphanumeric (keep underscores), truncate to 24 chars. Change `_next_config_path(data_dir)` -> `_next_config_path(data_dir, form_title)`: generate slug, scan data_dir for `{slug}_form_config.json`, `{slug}_2_form_config.json`, etc., return first non-existent variant. Also return the `base_name` for downstream use.

2. `strategy_generator.py` - Replace `_extract_suffix(config_path)` (currently extracts numeric N) with `_extract_base_name(config_path)` that extracts everything before `_form_config.json`. Use `base_name` for: `{base_name}_research_basis.json`, `{base_name}_research_analysis.json`, `{base_name}_strategy.json`.

3. `orchestrator.py` - Thread `base_name` through run functions; use for `{base_name}_responses.json`. Update `_sessions[session_id]`.

4. `main.py` - Store `base_name` in `_sessions[session_id]` state.

**File naming examples:**
- Form: "Badanie bezpieczenstwa biometrii" -> slug `badanie_bezpieczenst` (24 chars)
- Files: `badanie_bezpieczenst_form_config.json`, `badanie_bezpieczenst_strategy.json`, `badanie_bezpieczenst_responses.json`
- Second run: `badanie_bezpieczenst_2_form_config.json`, etc.

---

## Phase 2: Firestore Pipeline Persistence

### Firestore Structure
All step JSONs are well under 1MB - store everything as fields directly on the pipeline document (no subcollections).

```
pipelines/{pipeline_id}
  user_uid: string
  form_url: string
  form_title: string
  base_name: string              # local file slug
  total_responses: int
  status: "in_progress" | "completed" | "failed"
  created_at: timestamp
  completed_at: timestamp | null
  error: string | null
  step_form_config: {...}
  step_research_basis: {...}
  step_research_analysis: {...}
  step_strategy: {...}
  step_responses: [...]          # AI pool only, <=200 items (MAX_AI_RESPONSES=200)
```

Note: Step 3 generates min(total_responses, 200) AI responses. Step 5 batches/reshuffles that pool to reach total_responses. So `step_responses` saves the AI pool (<=200), and `total_responses` is just metadata.

### `firestore_service.py` - New functions:
- `create_pipeline(uid, form_url, form_title, total_responses, base_name)` -> pipeline_id (UUID)
- `save_pipeline_step(pipeline_id, step_key, data)` - `update()` doc with `{"step_{step_key}": data}`
- `complete_pipeline(pipeline_id)` - status = "completed", completed_at = now
- `fail_pipeline(pipeline_id, error)` - status = "failed", error = msg
- `get_user_pipelines(uid, limit=20)` -> metadata list only (exclude step_* fields via select())
- `get_pipeline(pipeline_id, uid)` -> full doc dict (with uid ownership check)

### `orchestrator.py` - Add Firestore calls:
- Receive `uid` and `pipeline_id` parameters (optional - None when AUTH_DISABLED)
- After Step 1: `save_pipeline_step(pipeline_id, 'form_config', config)`
- After Step 2.1: `save_pipeline_step(pipeline_id, 'research_basis', data)`
- After Step 2.2: `save_pipeline_step(pipeline_id, 'research_analysis', data)`
- After Step 2.3: `save_pipeline_step(pipeline_id, 'strategy', data)`
- After Step 3: `save_pipeline_step(pipeline_id, 'responses', responses)`
- After Step 5: `complete_pipeline(pipeline_id)`
- On exception: `fail_pipeline(pipeline_id, error_msg)`

### `main.py` - Pipeline lifecycle + new endpoints:
- On `POST /run`: call `create_pipeline(uid, ...)` -> get `pipeline_id`, pass to worker thread
- On `POST /session`: call `create_pipeline(uid, ...)`, store `pipeline_id` in `_sessions[session_id]`
- On step-by-step advance: pass `pipeline_id` to step runners

New endpoints:
- `GET /history` - auth required, calls `get_user_pipelines(uid)`, returns list (no step data)
- `GET /history/{pipeline_id}` - auth required, validates uid, returns full pipeline doc
- `POST /history/{pipeline_id}/resubmit` with `ResubmitHistoryRequest(total_responses)`:
  - Loads `step_form_config` + `step_responses` from Firestore doc
  - Runs Steps 4-5 (shuffle + submit) with loaded data
  - Returns job_id for SSE streaming

AUTH_DISABLED handling: if uid is None, skip all Firestore pipeline operations (no-op guard at top of each function).

---

## Phase 3: Frontend History UI

### New `useHistory.ts` hook:
- State: `pipelines: PipelineRecord[]`, `loading`, `error`
- `fetchHistory()`: GET /history
- Called on mount when authenticated

### `usePipeline.ts` - Add method:
- `resubmitFromHistory(pipelineId, totalResponses)`: POST `/history/{pipeline_id}/resubmit`, then stream SSE

### New `PipelineHistory.tsx` component:
- Shows list: form title, date, status badge, total_responses
- Per-row "Resubmit" button -> opens count input -> calls resubmitFromHistory
- Only shown when authenticated

### `App.tsx` - Integrate history:
- Show `PipelineHistory` as collapsible section below main form (avoids routing complexity)
- Refresh history list after each successful pipeline completion

---

## Relevant Files
- `backend/firestore_service.py` - add 6 new functions
- `backend/forms_extractor.py` - `_slugify()`, updated `_next_config_path()`
- `backend/strategy_generator.py` - replace `_extract_suffix()` with `_extract_base_name()`
- `backend/orchestrator.py` - uid/pipeline_id params, Firestore save calls
- `backend/main.py` - pass uid to pipeline, 3 new endpoints
- `frontend/src/hooks/usePipeline.ts` - add `resubmitFromHistory()`
- `frontend/src/hooks/useHistory.ts` - new file
- `frontend/src/components/PipelineHistory.tsx` - new file
- `frontend/src/App.tsx` - integrate history component

---

## Verification
1. Full pipeline run -> `data/{slug}_form_config.json` created with new naming
2. Same form again -> `{slug}_2_form_config.json` created
3. Firestore console -> single pipeline doc with all step_* fields populated
4. `GET /history` returns pipeline records (no step data)
5. `POST /history/{id}/resubmit` streams Steps 4-5 successfully
6. Session mode: each step advance saves to Firestore
7. Frontend: history list appears, resubmit button works end-to-end
8. AUTH_DISABLED=true: pipeline runs, no Firestore calls made

---

## Decisions
- Local files KEPT alongside Firestore (backward compat + debugging)
- No subcollections - all step data as fields on the pipeline doc (all well under 1MB)
- AUTH_DISABLED -> skip Firestore silently (uid = None guard in each function)
- pipeline_id = UUID; slug stored as `base_name` field
- `_n` suffix starts at `_2` (first run has no suffix)
- History UI: collapsible section in App.tsx (no router needed)
- History detail: metadata list + resubmit only for MVP (no strategy/responses viewer)
