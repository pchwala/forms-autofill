from __future__ import annotations

import asyncio
import json
import os
import pathlib
import re
import threading
import uuid
from typing import AsyncGenerator, Callable

import firebase_admin
from firebase_admin import auth as firebase_auth, credentials, firestore as fb_firestore
from fastapi import FastAPI, Form, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .firestore_service import (
    can_run_pipeline,
    consume_free_use,
    get_or_create_user,
    get_user_status,
    mark_paid,
)
from .orchestrator import (
    run_pipeline,
    step1_extract,
    step2_strategy,
    step3_generate,
    step4_shuffle,
    step5_submit,
)

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


class SessionRequest(BaseModel):
    form_url: str
    total_responses: int = 100


@app.post("/run")
async def run(req: RunRequest, authorization: str | None = Header(default=None)):
    user = _verify(authorization)
    uid, email = user["uid"], user["email"]
    if not AUTH_DISABLED:
        get_or_create_user(uid, email)
        if not can_run_pipeline(uid):
            raise HTTPException(status_code=402, detail="Free run already used; payment required")
        consume_free_use(uid)
    loop = asyncio.get_running_loop()
    job_id, _, emit = _make_job(loop)

    def worker() -> None:
        try:
            responses = run_pipeline(req.form_url, req.total_responses, emit)
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["result"] = responses
            emit({"type": "done", "total": len(responses)})
        except Exception as exc:
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = str(exc)
            emit({"type": "error", "message": str(exc)})

    threading.Thread(target=worker, daemon=True).start()
    return {"job_id": job_id}


@app.post("/session")
async def create_session(req: SessionRequest, authorization: str | None = Header(default=None)):
    user = _verify(authorization)
    uid, email = user["uid"], user["email"]
    if not AUTH_DISABLED:
        get_or_create_user(uid, email)
        if not can_run_pipeline(uid):
            raise HTTPException(status_code=402, detail="Free run already used; payment required")
        consume_free_use(uid)
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "form_url": req.form_url,
        "total_responses": req.total_responses,
        "current_step": 0,
        "status": "idle",
        "config_path": None,
        "strategy_path": None,
        "responses": None,
    }
    return {"session_id": session_id}


@app.get("/session/{session_id}")
async def get_session(session_id: str, authorization: str | None = Header(default=None)):
    user = _verify(authorization)
    if not AUTH_DISABLED:
        get_or_create_user(user["uid"], user["email"])
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
    if not AUTH_DISABLED:
        get_or_create_user(user["uid"], user["email"])
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

            if next_step == 1:
                result = step1_extract(s["form_url"], data_dir, emit)
                s["config_path"] = result
            elif next_step == 2:
                result = step2_strategy(s["config_path"], emit)
                s["strategy_path"] = result
            elif next_step == 3:
                result = step3_generate(
                    s["config_path"], s["strategy_path"], s["total_responses"], emit
                )
                s["responses"] = result
            elif next_step == 4:
                result = step4_shuffle(s["responses"], emit)
                s["responses"] = result
            elif next_step == 5:
                step5_submit(s["config_path"], s["responses"], emit)
                result = s["responses"]

            s["current_step"] = next_step
            s["status"] = "done" if next_step == 5 else "idle"
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["result"] = result if next_step == 5 else None
            emit({"type": "step_complete", "step": next_step})
            if next_step == 5:
                emit({"type": "done", "total": len(s["responses"])})
                _sessions.pop(session_id, None)
        except Exception as exc:
            s["status"] = "error"
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = str(exc)
            emit({"type": "error", "message": str(exc)})
            _sessions.pop(session_id, None)

    threading.Thread(target=worker, daemon=True).start()
    return {"job_id": job_id, "step": next_step}


@app.get("/stream/{job_id}")
async def stream(job_id: str, authorization: str | None = Header(default=None)):
    user = _verify(authorization)
    if not AUTH_DISABLED:
        get_or_create_user(user["uid"], user["email"])
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
        _jobs.pop(job_id, None)

    return StreamingResponse(generator(), media_type="text/event-stream")


@app.get("/result/{job_id}")
async def result(job_id: str, authorization: str | None = Header(default=None)):
    user = _verify(authorization)
    if not AUTH_DISABLED:
        get_or_create_user(user["uid"], user["email"])
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = _jobs[job_id]
    if job["status"] == "running":
        return {"status": "running"}
    if job["status"] == "error":
        return {"status": "error", "error": job.get("error", "unknown")}
    return {"status": "done", "total": len(job["result"]), "responses": job["result"]}


@app.post("/webhook/kofi")
async def webhook_kofi(data: str = Form(...)):
    """Unauthenticated Ko-fi payment webhook. Secured by verification_token."""
    kofi_token = os.getenv("KOFI_VERIFICATION_TOKEN", "")

    try:
        payload = json.loads(data)
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid payload")

    if payload.get("verification_token") != kofi_token:
        raise HTTPException(status_code=403, detail="Invalid verification token")

    try:
        amount = float(payload.get("amount", 0))
    except (TypeError, ValueError):
        return {"ok": True}

    if amount < 5.0:
        return {"ok": True}

    message = payload.get("message") or ""
    match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", message)
    if not match:
        return {"ok": True}

    email = match.group(0)
    try:
        kofi_user = firebase_auth.get_user_by_email(email)
    except Exception:
        return {"ok": True}

    mark_paid(kofi_user.uid, email, amount)
    return {"ok": True}


@app.get("/user/status")
async def user_status(authorization: str | None = Header(default=None)):
    user = _verify(authorization)
    if AUTH_DISABLED:
        return {"free_used": False, "paid": False}
    get_or_create_user(user["uid"], user["email"])
    return get_user_status(user["uid"])