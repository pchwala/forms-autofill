from __future__ import annotations

import asyncio
import json
import os
import pathlib
import threading
import uuid
from typing import AsyncGenerator, Callable

import firebase_admin
import stripe
from firebase_admin import auth as firebase_auth, credentials, firestore as fb_firestore
from fastapi import FastAPI, Header, HTTPException, Request
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
    get_pipeline,
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

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
_STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
_APP_URL = os.getenv(
    "APP_URL",
    os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")[0].strip(),
)

PACKS: dict[str, dict] = {
    "small":  {"credits": 20,  "pln": 499,  "price_id_pln": "price_1TisGhKEGI0EbMNbnbvPSCGl"},
    "medium": {"credits": 100, "pln": 2125, "price_id_pln": "price_1TisGhKEGI0EbMNbf1Pg7vN6"},
    "large":  {"credits": 200, "pln": 3750, "price_id_pln": "price_1TisGgKEGI0EbMNbfGVqfN4B"},
}

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


_cred = _load_firebase_credentials()
firebase_admin.initialize_app(_cred)
fb_firestore.client()  # Validate Firestore connection at startup

# _jobs holds the SSE queue for a *live* run only. It is intentionally in-memory: a dead
# process means a dead run, and credits are charged after submission (so no money rides on
# it). It is never the source of truth for pipeline state.
_jobs: dict[str, dict] = {}


def _load_pipeline_record(pipeline_id: str, uid: str) -> dict | None:
    """Return the persisted pipeline record needed to run a submit, or None if unavailable.

    Shape: {uid, base_name, form_config, strategy, preview, status}, read from Firestore.
    Returns None when the record is missing, not owned by the caller, or the
    form_config/strategy haven't been persisted yet (preview not ready).
    """
    doc = get_pipeline(pipeline_id, uid)
    if doc is None:
        return None
    form_config = doc.get("step_form_config")
    strategy = doc.get("step_strategy")
    if form_config is None or strategy is None:
        return None
    return {
        "uid": doc.get("user_uid"),
        "base_name": doc.get("base_name"),
        "form_config": form_config,
        "strategy": strategy,
        "preview": doc.get("preview"),
        "status": doc.get("status"),
    }


def _verify(authorization: str | None) -> dict[str, str]:
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
    _jobs[job_id] = {"queue": queue}

    def emit(event: dict) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, event)

    return job_id, queue, emit


@app.get("/stream/{job_id}")
async def stream(job_id: str, authorization: str | None = Header(default=None)):
    _verify(authorization)
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    async def generator() -> AsyncGenerator[str, None]:
        q = _jobs[job_id]["queue"]
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=30)
                except asyncio.TimeoutError:
                    yield 'data: {"type":"ping"}\n\n'
                    continue
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") in ("done", "error", "step_complete"):
                    break
        finally:
            # Each job is streamed exactly once; drop it so _jobs doesn't grow unbounded.
            _jobs.pop(job_id, None)

    return StreamingResponse(generator(), media_type="text/event-stream")


@app.get("/history")
async def get_history(authorization: str | None = Header(default=None)):
    user = _verify(authorization)
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
    get_or_create_user(uid, email)

    # One id end-to-end: the Firestore doc id == the id the client holds.
    pipeline_id = str(uuid.uuid4())

    loop = asyncio.get_running_loop()
    job_id, _, emit = _make_job(loop)

    def worker() -> None:
        try:
            data_dir = pathlib.Path("data")
            data_dir.mkdir(exist_ok=True)

            config_path, base_name = step1_extract(req.form_url, data_dir, emit)
            config_data = json.loads(config_path.read_text(encoding="utf-8"))
            form_title = config_data.get("form_title", "")

            create_pipeline(
                pipeline_id, uid, req.form_url, form_title, req.total_responses, base_name,
                desire_prompt=req.desire_prompt,
            )
            save_pipeline_step(pipeline_id, "form_config", config_data)

            strategy_path = step2_strategy(
                config_path, emit, pipeline_id=pipeline_id, desire_prompt=req.desire_prompt
            )
            strategy_data = json.loads(strategy_path.read_text(encoding="utf-8"))
            preview_data = compute_preview(strategy_data, config_data)

            update_pipeline(pipeline_id, {"status": "preview_ready", "preview": preview_data})

            emit({"type": "result", "key": "preview", "data": preview_data})
            emit({"type": "done", "pipeline_id": pipeline_id})
        except Exception as exc:
            fail_pipeline(pipeline_id, str(exc))
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

    record = _load_pipeline_record(pipeline_id, uid)
    if record is None or record.get("status") == "in_progress":
        raise HTTPException(status_code=404, detail="Pipeline not found or not ready")

    # 1 credit = 1 submitted response. Require enough balance up front; the actual charge
    # (successful submissions only) is applied by the worker once the run completes.
    if get_credits(uid) < req.total_responses:
        raise HTTPException(status_code=402, detail="Insufficient credits; payment required")

    form_config = record["form_config"]

    try:
        filtered = filter_and_renormalize_personas(record["strategy"], req.selected_persona_codes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    update_pipeline(
        pipeline_id,
        {"status": "submitting", "selected_persona_codes": req.selected_persona_codes},
    )

    loop = asyncio.get_running_loop()
    job_id, _, emit = _make_job(loop)

    def worker() -> None:
        try:
            responses = step3_generate(
                form_config, filtered, req.total_responses, emit, pipeline_id=pipeline_id
            )
            shuffled = step4_shuffle(responses, emit)
            succeeded = step5_submit(form_config, shuffled, req.total_responses, emit)
            consume_credits(uid, succeeded)  # charge only confirmed submissions
            complete_pipeline(pipeline_id)
            emit({"type": "done", "total": succeeded, "pipeline_id": pipeline_id})
        except Exception as exc:
            # Nothing was charged; leave the record resubmittable.
            fail_pipeline(pipeline_id, str(exc))
            emit({"type": "error", "message": str(exc)})

    threading.Thread(target=worker, daemon=True).start()
    return {"job_id": job_id}


@app.get("/pipelines/{pipeline_id}")
async def get_pipeline_status(
    pipeline_id: str, authorization: str | None = Header(default=None)
):
    """Restore a pipeline's preview/status from the authoritative store (used by the frontend
    after a reload or the Stripe redirect, so nothing is re-run)."""
    user = _verify(authorization)
    uid = user["uid"]
    doc = get_pipeline(pipeline_id, uid)
    if doc is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return {
        "status": doc.get("status"),
        "preview": doc.get("preview"),
        "total_responses": doc.get("total_responses"),
        "form_title": doc.get("form_title"),
        "selected_persona_codes": doc.get("selected_persona_codes"),
    }


# ---------------------------------------------------------------------------
# Billing — Stripe Checkout
# ---------------------------------------------------------------------------


async def _fulfill_checkout(session: dict) -> None:
    """Grant credits for a completed Stripe Checkout session (idempotent)."""
    uid = session["metadata"]["uid"]
    credits = int(session["metadata"]["credits"])
    add_credits(uid, credits, idempotency_key=session["id"])


@app.get("/billing/packs")
async def billing_packs():
    """Return available credit packs (no auth required)."""
    return PACKS


class CheckoutRequest(BaseModel):
    pack: str
    quantity: int = 1


@app.post("/billing/checkout")
async def billing_checkout(
    req: CheckoutRequest, authorization: str | None = Header(default=None)
):
    """Create a Stripe Checkout Session and return its URL."""
    user = _verify(authorization)
    uid = user["uid"]

    if req.pack not in PACKS:
        raise HTTPException(status_code=400, detail=f"Unknown pack: {req.pack}")
    if req.quantity < 1:
        raise HTTPException(status_code=400, detail="quantity must be at least 1")

    pack = PACKS[req.pack]
    total_credits = pack["credits"] * req.quantity

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{"price": pack["price_id_pln"], "quantity": req.quantity}],
            metadata={"uid": uid, "credits": str(total_credits)},
            success_url=f"{_APP_URL}/?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{_APP_URL}/?checkout=cancel",
        )
    except stripe.StripeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"url": session.url}


@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Stripe webhook endpoint — verifies signature and fulfills completed checkouts."""
    body = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(body, sig_header, _STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        await _fulfill_checkout(event["data"]["object"])

    return {"ok": True}


class ConfirmRequest(BaseModel):
    session_id: str


@app.post("/billing/confirm")
async def billing_confirm(
    req: ConfirmRequest, authorization: str | None = Header(default=None)
):
    """On-return fallback: confirm a Stripe session and grant credits if paid.

    Called by the frontend when returning from Stripe Checkout, so fulfillment
    doesn't depend on the webhook arriving first. Idempotent — safe to call even
    if the webhook already ran.
    """
    user = _verify(authorization)
    uid = user["uid"]

    try:
        session = stripe.checkout.Session.retrieve(req.session_id)
    except stripe.StripeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if session.get("payment_status") == "paid" and session.get("metadata", {}).get("uid") == uid:
        await _fulfill_checkout(session)

    return {"credits": get_credits(uid)}
