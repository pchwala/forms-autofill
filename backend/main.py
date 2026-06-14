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
    consume_credits,
    create_pipeline,
    fail_pipeline,
    get_credits,
    get_or_create_user,
    get_user_pipelines,
    get_user_status,
    save_pipeline_step,
    update_pipeline,
)
from .orchestrator import (
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
    # A relative path is resolved both against the current working directory and
    # against this package directory (uvicorn is typically launched from the repo
    # root, while the credentials file lives next to this module in backend/).
    candidate = pathlib.Path(creds_env)
    if not candidate.is_file():
        candidate = pathlib.Path(__file__).resolve().parent / creds_env
    if candidate.is_file():
        return credentials.Certificate(str(candidate))

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
    """Paid phase: generate + shuffle + submit responses for the selected personas, then
    charge 1 credit per confirmed submission. Returns 402 when the balance can't cover the
    requested response count. Credits are deducted *after* submission, so nothing is consumed
    (and nothing needs refunding) if the run fails."""
    user = _verify(authorization)
    uid = user["uid"]

    pipe = _pipelines.get(pipeline_id)
    if pipe is None or pipe.get("status") not in ("preview_ready", "completed"):
        raise HTTPException(status_code=404, detail="Pipeline not found or not ready")
    if not AUTH_DISABLED and pipe.get("uid") != uid:
        raise HTTPException(status_code=403, detail="Not your pipeline")

    # 1 credit = 1 submitted response. Require enough balance up front; the actual charge
    # (successful submissions only) is applied by the worker once the run completes.
    if not AUTH_DISABLED and get_credits(uid) < req.total_responses:
        raise HTTPException(status_code=402, detail="Insufficient credits; payment required")

    config_path: pathlib.Path = pipe["config_path"]
    strategy_path: pathlib.Path = pipe["strategy_path"]
    fs_id = pipe.get("fs_id")
    strategy_data = json.loads(strategy_path.read_text(encoding="utf-8"))

    try:
        filtered = filter_and_renormalize_personas(strategy_data, req.selected_persona_codes)
    except ValueError as exc:
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
            succeeded = step5_submit(config_path, shuffled, req.total_responses, emit)
            if not AUTH_DISABLED:
                consume_credits(uid, succeeded)  # charge only confirmed submissions
                complete_pipeline(fs_id)
            pipe["status"] = "completed"
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["result"] = shuffled
            emit({"type": "done", "total": succeeded, "pipeline_id": pipeline_id})
        except Exception as exc:
            pipe["status"] = "preview_ready"  # allow retry; nothing was charged
            if not AUTH_DISABLED:
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