from __future__ import annotations

import asyncio
import json
import os
import pathlib
import threading
import uuid
from typing import AsyncGenerator, Callable

import firebase_admin
from firebase_admin import auth as firebase_auth, credentials, firestore as fb_firestore
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from .firestore_service import (
    add_credits,
    complete_pipeline,
    consume_credit,
    create_pipeline,
    fail_pipeline,
    get_or_create_user,
    get_pipeline,
    get_user_pipelines,
    get_user_status,
    save_pipeline_step,
    update_pipeline,
)
from .orchestrator import (
    run_pipeline,
    step1_extract,
    step2_strategy,
    step3_generate,
    step4_shuffle,
    step5_submit,
)
from .preview import compute_preview, filter_and_renormalize_personas

# Credits granted per placeholder "payment". Stripe will replace /credits/grant later.
CREDITS_PER_PURCHASE = int(os.getenv("CREDITS_PER_PURCHASE", "1"))

app = FastAPI(title="Forms Autofill API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _load_firebase_credentials() -> credentials.Base:
    creds_env = os.getenv("FIREBASE_CREDENTIALS_JSON", "").strip()
    if not creds_env:
        raise ValueError("FIREBASE_CREDENTIALS_JSON is required")

    # Accept either a file path or raw JSON content in the env var.
    if pathlib.Path(creds_env).is_file():
        return credentials.Certificate(creds_env)

    try:
        creds_data = json.loads(creds_env)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "FIREBASE_CREDENTIALS_JSON must be a valid JSON string or a file path"
        ) from exc

    return credentials.Certificate(creds_data)


AUTH_DISABLED = os.getenv("AUTH_DISABLED", "false").lower() == "true"

if not AUTH_DISABLED:
    _cred = _load_firebase_credentials()
    firebase_admin.initialize_app(_cred)
    fb_firestore.client()  # Validate Firestore connection at startup

_jobs: dict[str, dict] = {}
_sessions: dict[str, dict] = {}
# Preview/submit pipelines held in-process between the free preview and the paid
# submit (the placeholder paywall is a dialog, so the process stays up in between).
# Firestore persistence (when authed) is for history; this is the submit source of truth.
_pipelines: dict[str, dict] = {}


def _verify(authorization: str | None) -> dict[str, str]:
    if AUTH_DISABLED:
        return {"uid": "dev", "email": "dev@local"}
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization[len("Bearer "):]
    try:
        decoded = firebase_auth.verify_id_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"uid": decoded["uid"], "email": decoded.get("email", "")}


def _make_job(loop: asyncio.AbstractEventLoop) -> tuple[str, asyncio.Queue, Callable[[dict], None]]:
    job_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    _jobs[job_id] = {"status": "running", "queue": queue, "result": None}

    def emit(event: dict) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, event)

    return job_id, queue, emit


class RunRequest(BaseModel):
    form_url: str
    total_responses: int = 100

    @field_validator("total_responses")
    @classmethod
    def _validate_total(cls, v: int) -> int:
        if not (1 <= v <= 1000):
            raise ValueError("total_responses must be between 1 and 1000")
        return v


class SessionRequest(BaseModel):
    form_url: str
    total_responses: int = 100

    @field_validator("total_responses")
    @classmethod
    def _validate_total(cls, v: int) -> int:
        if not (1 <= v <= 1000):
            raise ValueError("total_responses must be between 1 and 1000")
        return v


class ResubmitRequest(BaseModel):
    result_id: str
    total_responses: int

    @field_validator("total_responses")
    @classmethod
    def _validate_total(cls, v: int) -> int:
        if not (1 <= v <= 1000):
            raise ValueError("total_responses must be between 1 and 1000")
        return v


class ResubmitSessionRequest(BaseModel):
    total_responses: int

    @field_validator("total_responses")
    @classmethod
    def _validate_total(cls, v: int) -> int:
        if not (1 <= v <= 1000):
            raise ValueError("total_responses must be between 1 and 1000")
        return v


class ResubmitHistoryRequest(BaseModel):
    total_responses: int

    @field_validator("total_responses")
    @classmethod
    def _validate_total(cls, v: int) -> int:
        if not (1 <= v <= 1000):
            raise ValueError("total_responses must be between 1 and 1000")
        return v


@app.post("/run")
async def run(req: RunRequest, authorization: str | None = Header(default=None)):
    # Legacy all-in-one endpoint, superseded by /preview + /pipelines/{id}/submit.
    # Kept for reference; not called by the frontend.
    user = _verify(authorization)
    uid, email = user["uid"], user["email"]
    if not AUTH_DISABLED:
        get_or_create_user(uid, email)
    loop = asyncio.get_running_loop()
    job_id, _, emit = _make_job(loop)

    def worker() -> None:
        try:
            uid_for_pipeline = None if AUTH_DISABLED else uid
            config_path, responses = run_pipeline(req.form_url, req.total_responses, emit, uid=uid_for_pipeline)
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["result"] = responses
            _jobs[job_id]["config_path"] = config_path
            emit({"type": "done", "total": len(responses), "result_id": job_id})
        except Exception as exc:
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = str(exc)
            emit({"type": "error", "message": str(exc)})

    threading.Thread(target=worker, daemon=True).start()
    return {"job_id": job_id}


@app.post("/session")
async def create_session(req: SessionRequest, authorization: str | None = Header(default=None)):
    # Legacy step-by-step session endpoint; retained but not used by the frontend.
    user = _verify(authorization)
    uid, email = user["uid"], user["email"]
    if not AUTH_DISABLED:
        get_or_create_user(uid, email)
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "form_url": req.form_url,
        "total_responses": req.total_responses,
        "current_step": 0,
        "status": "idle",
        "config_path": None,
        "strategy_path": None,
        "responses": None,
        "base_name": None,
        "pipeline_id": None,
    }
    return {"session_id": session_id}


@app.get("/session/{session_id}")
async def get_session(session_id: str, authorization: str | None = Header(default=None)):
    user = _verify(authorization)
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    s = _sessions[session_id]
    return {
        "session_id": session_id,
        "current_step": s["current_step"],
        "status": s["status"],
        "total_steps": 5,
    }


@app.post("/session/{session_id}/advance")
async def advance_session(session_id: str, authorization: str | None = Header(default=None)):
    user = _verify(authorization)
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    s = _sessions[session_id]
    if s["status"] == "running":
        raise HTTPException(status_code=409, detail="Step already running")
    if s["current_step"] >= 5:
        raise HTTPException(status_code=409, detail="Pipeline already complete")

    next_step = s["current_step"] + 1
    s["status"] = "running"

    loop = asyncio.get_running_loop()
    job_id, _, emit = _make_job(loop)

    def worker() -> None:
        try:
            data_dir = pathlib.Path("data")
            data_dir.mkdir(exist_ok=True)
            result = None

            if next_step == 1:
                config_path, base_name = step1_extract(s["form_url"], data_dir, emit)
                s["config_path"] = config_path
                s["base_name"] = base_name
                config_data = json.loads(config_path.read_text(encoding="utf-8"))
                form_title = config_data.get("form_title", "")
                uid_for_pipeline = None if AUTH_DISABLED else user["uid"]
                pipeline_id = create_pipeline(uid_for_pipeline, s["form_url"], form_title, s["total_responses"], base_name)
                s["pipeline_id"] = pipeline_id
                save_pipeline_step(pipeline_id, "form_config", config_data)
                result = config_path
            elif next_step == 2:
                result = step2_strategy(s["config_path"], emit, pipeline_id=s["pipeline_id"])
                s["strategy_path"] = result
            elif next_step == 3:
                result = step3_generate(
                    s["config_path"], s["strategy_path"], s["total_responses"], emit,
                    pipeline_id=s["pipeline_id"],
                )
                s["responses"] = result
            elif next_step == 4:
                result = step4_shuffle(s["responses"], emit)
                s["responses"] = result
            elif next_step == 5:
                step5_submit(s["config_path"], s["responses"], s["total_responses"], emit)
                complete_pipeline(s["pipeline_id"])
                result = s["responses"]

            s["current_step"] = next_step
            s["status"] = "completed" if next_step == 5 else "idle"
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["result"] = result if next_step == 5 else None
            emit({"type": "step_complete", "step": next_step})
            if next_step == 5:
                emit({"type": "done", "total": len(s["responses"]), "session_id": session_id})
        except Exception as exc:
            s["status"] = "error"
            fail_pipeline(s.get("pipeline_id"), str(exc))
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = str(exc)
            emit({"type": "error", "message": str(exc)})

    threading.Thread(target=worker, daemon=True).start()
    return {"job_id": job_id, "step": next_step}


@app.get("/stream/{job_id}")
async def stream(job_id: str, authorization: str | None = Header(default=None)):
    user = _verify(authorization)
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    async def generator() -> AsyncGenerator[str, None]:
        q = _jobs[job_id]["queue"]
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=30)
            except asyncio.TimeoutError:
                yield 'data: {"type":"ping"}\n\n'
                continue
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("type") in ("done", "error", "step_complete"):
                break
        # Do NOT pop the job — it may be needed for resubmit

    return StreamingResponse(generator(), media_type="text/event-stream")


@app.get("/result/{job_id}")
async def result(job_id: str, authorization: str | None = Header(default=None)):
    user = _verify(authorization)
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = _jobs[job_id]
    if job["status"] == "running":
        return {"status": "running"}
    if job["status"] == "error":
        return {"status": "error", "error": job.get("error", "unknown")}
    return {"status": "done", "total": len(job["result"]), "responses": job["result"]}


@app.post("/resubmit")
async def resubmit(req: ResubmitRequest, authorization: str | None = Header(default=None)):
    user = _verify(authorization)
    if not AUTH_DISABLED:
        get_or_create_user(user["uid"], user["email"])
    job = _jobs.get(req.result_id)
    if job is None or job["status"] != "done":
        raise HTTPException(status_code=404, detail="Result not found or pipeline not complete")

    config_path: pathlib.Path = job["config_path"]
    responses: list[dict] = job["result"]

    loop = asyncio.get_running_loop()
    new_job_id, _, emit = _make_job(loop)

    def worker() -> None:
        try:
            shuffled = step4_shuffle(responses, emit)
            step5_submit(config_path, shuffled, req.total_responses, emit)
            _jobs[new_job_id]["status"] = "done"
            _jobs[new_job_id]["result"] = shuffled
            _jobs[new_job_id]["config_path"] = config_path
            emit({"type": "done", "total": req.total_responses, "result_id": new_job_id})
        except Exception as exc:
            _jobs[new_job_id]["status"] = "error"
            _jobs[new_job_id]["error"] = str(exc)
            emit({"type": "error", "message": str(exc)})

    threading.Thread(target=worker, daemon=True).start()
    return {"job_id": new_job_id}


@app.post("/session/{session_id}/resubmit")
async def resubmit_session(session_id: str, req: ResubmitSessionRequest, authorization: str | None = Header(default=None)):
    user = _verify(authorization)
    if not AUTH_DISABLED:
        get_or_create_user(user["uid"], user["email"])
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    s = _sessions[session_id]
    if s["status"] != "completed":
        raise HTTPException(status_code=409, detail="Pipeline not complete; cannot resubmit")

    config_path: pathlib.Path = s["config_path"]
    responses: list[dict] = s["responses"]

    loop = asyncio.get_running_loop()
    job_id, _, emit = _make_job(loop)

    def worker() -> None:
        try:
            shuffled = step4_shuffle(responses, emit)
            step5_submit(config_path, shuffled, req.total_responses, emit)
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["result"] = shuffled
            emit({"type": "done", "total": req.total_responses, "session_id": session_id})
        except Exception as exc:
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = str(exc)
            emit({"type": "error", "message": str(exc)})

    threading.Thread(target=worker, daemon=True).start()
    return {"job_id": job_id}


@app.get("/history")
async def get_history(authorization: str | None = Header(default=None)):
    user = _verify(authorization)
    if AUTH_DISABLED:
        return []
    try:
        pipelines = get_user_pipelines(user["uid"])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    for p in pipelines:
        for key in ("created_at", "completed_at"):
            val = p.get(key)
            if val is not None and hasattr(val, "isoformat"):
                p[key] = val.isoformat()
    return pipelines


@app.get("/history/{pipeline_id}")
async def get_history_detail(pipeline_id: str, authorization: str | None = Header(default=None)):
    user = _verify(authorization)
    if AUTH_DISABLED:
        raise HTTPException(status_code=404, detail="History not available in dev mode")
    doc = get_pipeline(pipeline_id, user["uid"])
    if doc is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    for key in ("created_at", "completed_at"):
        val = doc.get(key)
        if val is not None and hasattr(val, "isoformat"):
            doc[key] = val.isoformat()
    return doc


@app.post("/history/{pipeline_id}/resubmit")
async def resubmit_history(
    pipeline_id: str,
    req: ResubmitHistoryRequest,
    authorization: str | None = Header(default=None),
):
    user = _verify(authorization)
    if AUTH_DISABLED:
        raise HTTPException(status_code=404, detail="History not available in dev mode")
    doc = get_pipeline(pipeline_id, user["uid"])
    if doc is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    config_data = doc.get("step_form_config")
    responses = doc.get("step_responses")
    if not config_data or not responses:
        raise HTTPException(status_code=409, detail="Pipeline data incomplete for resubmit")

    base_name = doc.get("base_name", "")
    config_path = pathlib.Path("data") / f"{base_name}_form_config.json"
    if not config_path.exists():
        config_path.parent.mkdir(exist_ok=True)
        config_path.write_text(json.dumps(config_data), encoding="utf-8")

    loop = asyncio.get_running_loop()
    job_id, _, emit = _make_job(loop)

    def worker() -> None:
        try:
            shuffled = step4_shuffle(responses, emit)
            step5_submit(config_path, shuffled, req.total_responses, emit)
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["result"] = shuffled
            _jobs[job_id]["config_path"] = config_path
            emit({"type": "done", "total": req.total_responses, "result_id": job_id})
        except Exception as exc:
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = str(exc)
            emit({"type": "error", "message": str(exc)})

    threading.Thread(target=worker, daemon=True).start()
    return {"job_id": job_id}



@app.get("/user/status")
async def user_status(authorization: str | None = Header(default=None)):
    user = _verify(authorization)
    if AUTH_DISABLED:
        return {"credits": 999999}  # effectively unlimited in dev
    return get_user_status(user["uid"])


# ---------------------------------------------------------------------------
# Preview → paywall → submit flow
# ---------------------------------------------------------------------------


class PreviewRequest(BaseModel):
    form_url: str
    total_responses: int = 100
    desire_prompt: str | None = None

    @field_validator("total_responses")
    @classmethod
    def _validate_total(cls, v: int) -> int:
        if not (1 <= v <= 1000):
            raise ValueError("total_responses must be between 1 and 1000")
        return v


class SubmitRequest(BaseModel):
    selected_persona_codes: list[str]
    total_responses: int

    @field_validator("total_responses")
    @classmethod
    def _validate_total(cls, v: int) -> int:
        if not (1 <= v <= 1000):
            raise ValueError("total_responses must be between 1 and 1000")
        return v

    @field_validator("selected_persona_codes")
    @classmethod
    def _validate_codes(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("At least one persona must be selected")
        return v


@app.post("/preview")
async def preview(req: PreviewRequest, authorization: str | None = Header(default=None)):
    """Free phase: extract the form + generate a strategy, then return the predicted
    persona mix and answer distributions. No credit is consumed."""
    user = _verify(authorization)
    uid, email = user["uid"], user["email"]
    if not AUTH_DISABLED:
        get_or_create_user(uid, email)

    pipeline_id = str(uuid.uuid4())
    _pipelines[pipeline_id] = {
        "uid": uid,
        "status": "in_progress",
        "form_url": req.form_url,
        "total_responses": req.total_responses,
        "desire_prompt": req.desire_prompt,
        "config_path": None,
        "strategy_path": None,
        "base_name": None,
        "preview": None,
        "fs_id": None,  # Firestore pipeline id (when authed)
    }

    loop = asyncio.get_running_loop()
    job_id, _, emit = _make_job(loop)

    def worker() -> None:
        try:
            data_dir = pathlib.Path("data")
            data_dir.mkdir(exist_ok=True)

            config_path, base_name = step1_extract(req.form_url, data_dir, emit)
            config_data = json.loads(config_path.read_text(encoding="utf-8"))
            form_title = config_data.get("form_title", "")

            fs_id = None
            if not AUTH_DISABLED:
                fs_id = create_pipeline(
                    uid, req.form_url, form_title, req.total_responses, base_name,
                    desire_prompt=req.desire_prompt,
                )
                save_pipeline_step(fs_id, "form_config", config_data)

            strategy_path = step2_strategy(
                config_path, emit, pipeline_id=fs_id, desire_prompt=req.desire_prompt
            )
            strategy_data = json.loads(strategy_path.read_text(encoding="utf-8"))
            preview_data = compute_preview(strategy_data, config_data)

            _pipelines[pipeline_id].update(
                {
                    "status": "preview_ready",
                    "config_path": config_path,
                    "strategy_path": strategy_path,
                    "base_name": base_name,
                    "preview": preview_data,
                    "fs_id": fs_id,
                }
            )
            if not AUTH_DISABLED:
                update_pipeline(fs_id, {"status": "preview_ready", "preview": preview_data})

            emit({"type": "result", "key": "preview", "data": preview_data})
            emit({"type": "done", "pipeline_id": pipeline_id})
        except Exception as exc:
            _pipelines[pipeline_id]["status"] = "failed"
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = str(exc)
            emit({"type": "error", "message": str(exc)})

    threading.Thread(target=worker, daemon=True).start()
    return {"job_id": job_id, "pipeline_id": pipeline_id}


@app.post("/pipelines/{pipeline_id}/submit")
async def submit_pipeline(
    pipeline_id: str,
    req: SubmitRequest,
    authorization: str | None = Header(default=None),
):
    """Paid phase: consume a credit, then generate + shuffle + submit responses for the
    selected personas. Returns 402 when the user has no credits."""
    user = _verify(authorization)
    uid = user["uid"]

    pipe = _pipelines.get(pipeline_id)
    if pipe is None or pipe.get("status") not in ("preview_ready", "completed"):
        raise HTTPException(status_code=404, detail="Pipeline not found or not ready")
    if not AUTH_DISABLED and pipe.get("uid") != uid:
        raise HTTPException(status_code=403, detail="Not your pipeline")

    if not AUTH_DISABLED:
        if not consume_credit(uid):
            raise HTTPException(status_code=402, detail="No credits; payment required")

    config_path: pathlib.Path = pipe["config_path"]
    strategy_path: pathlib.Path = pipe["strategy_path"]
    fs_id = pipe.get("fs_id")
    strategy_data = json.loads(strategy_path.read_text(encoding="utf-8"))

    try:
        filtered = filter_and_renormalize_personas(strategy_data, req.selected_persona_codes)
    except ValueError as exc:
        if not AUTH_DISABLED:
            add_credits(uid, 1)  # refund — submission never ran
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Write a filtered strategy file for the response generator to consume.
    filtered_path = strategy_path.with_name(strategy_path.stem + "_filtered.json")
    filtered_path.write_text(json.dumps(filtered, ensure_ascii=False, indent=2), encoding="utf-8")

    if not AUTH_DISABLED:
        update_pipeline(
            fs_id,
            {"status": "submitting", "selected_persona_codes": req.selected_persona_codes},
        )

    loop = asyncio.get_running_loop()
    job_id, _, emit = _make_job(loop)

    def worker() -> None:
        try:
            responses = step3_generate(
                config_path, filtered_path, req.total_responses, emit, pipeline_id=fs_id
            )
            shuffled = step4_shuffle(responses, emit)
            step5_submit(config_path, shuffled, req.total_responses, emit)
            pipe["status"] = "completed"
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["result"] = shuffled
            if not AUTH_DISABLED:
                complete_pipeline(fs_id)
            emit({"type": "done", "total": req.total_responses, "pipeline_id": pipeline_id})
        except Exception as exc:
            pipe["status"] = "preview_ready"  # allow retry
            if not AUTH_DISABLED:
                add_credits(uid, 1)  # refund the credit on failure
                fail_pipeline(fs_id, str(exc))
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = str(exc)
            emit({"type": "error", "message": str(exc)})

    threading.Thread(target=worker, daemon=True).start()
    return {"job_id": job_id}


@app.post("/credits/grant")
async def credits_grant(authorization: str | None = Header(default=None)):
    """Placeholder paywall: grants credits without real payment.

    Replace with Stripe Checkout session creation + webhook-driven add_credits later.
    """
    user = _verify(authorization)
    if AUTH_DISABLED:
        return {"credits": 999999}
    get_or_create_user(user["uid"], user["email"])
    new_balance = add_credits(user["uid"], CREDITS_PER_PURCHASE)
    return {"credits": new_balance}