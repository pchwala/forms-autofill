from __future__ import annotations

import asyncio
import json
import os
import pathlib
import threading
import uuid
from typing import AsyncGenerator

import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# trigger build

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
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

AUTH_DISABLED = os.getenv("AUTH_DISABLED", "false").lower() == "true"

if not AUTH_DISABLED:
    cred_path = "/app/backend/firebase_credentials.json"
    if pathlib.Path(cred_path).is_file():
        _cred = credentials.Certificate(cred_path)
    else:
        _creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
        if _creds_json:
            _cred = credentials.Certificate(json.loads(_creds_json))
        else:
            _cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(_cred)

_jobs: dict[str, dict] = {}
_sessions: dict[str, dict] = {}


def _verify(authorization: str | None) -> None:
    if AUTH_DISABLED:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization[len("Bearer "):]
    try:
        firebase_auth.verify_id_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def _make_job(loop: asyncio.AbstractEventLoop) -> tuple[str, asyncio.Queue, callable]:
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
    _verify(authorization)
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
    _verify(authorization)
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
    _verify(authorization)
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
    _verify(authorization)
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
        except Exception as exc:
            s["status"] = "error"
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = str(exc)
            emit({"type": "error", "message": str(exc)})

    threading.Thread(target=worker, daemon=True).start()
    return {"job_id": job_id, "step": next_step}


@app.get("/stream/{job_id}")
async def stream(job_id: str, authorization: str | None = Header(default=None)):
    _verify(authorization)
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    async def generator() -> AsyncGenerator[str, None]:
        q = _jobs[job_id]["queue"]
        while True:
            event = await q.get()
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("type") in ("done", "error", "step_complete"):
                break

    return StreamingResponse(generator(), media_type="text/event-stream")


@app.get("/result/{job_id}")
async def result(job_id: str, authorization: str | None = Header(default=None)):
    _verify(authorization)
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = _jobs[job_id]
    if job["status"] == "running":
        return {"status": "running"}
    if job["status"] == "error":
        return {"status": "error", "error": job.get("error", "unknown")}
    return {"status": "done", "total": len(job["result"]), "responses": job["result"]}
