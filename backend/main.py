from __future__ import annotations

import asyncio
import json
import os
import secrets
import threading
import uuid
from typing import AsyncGenerator

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .orchestrator import run_pipeline

app = FastAPI(title="Forms Autofill API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_API_KEY = os.getenv("API_KEY", "")
_jobs: dict[str, dict] = {}


def _verify(key: str) -> None:
    if not _API_KEY or not secrets.compare_digest(key.encode(), _API_KEY.encode()):
        raise HTTPException(status_code=401, detail="Invalid API key")


class RunRequest(BaseModel):
    form_url: str
    total_responses: int = 100
    model: str = "gpt-4.1"


@app.post("/run")
async def run(req: RunRequest, x_api_key: str = Header(...)):
    _verify(x_api_key)
    job_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    _jobs[job_id] = {"status": "running", "queue": queue, "result": None}

    loop = asyncio.get_running_loop()

    def emit(event: dict) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, event)

    def worker() -> None:
        try:
            responses = run_pipeline(req.form_url, req.total_responses, req.model, emit)
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["result"] = responses
            emit({"type": "done", "total": len(responses)})
        except Exception as exc:
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = str(exc)
            emit({"type": "error", "message": str(exc)})

    threading.Thread(target=worker, daemon=True).start()
    return {"job_id": job_id}


@app.get("/stream/{job_id}")
async def stream(job_id: str, x_api_key: str = Header(...)):
    _verify(x_api_key)
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    async def generator() -> AsyncGenerator[str, None]:
        q = _jobs[job_id]["queue"]
        while True:
            event = await q.get()
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("type") in ("done", "error"):
                break

    return StreamingResponse(generator(), media_type="text/event-stream")


@app.get("/result/{job_id}")
async def result(job_id: str, x_api_key: str = Header(...)):
    _verify(x_api_key)
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = _jobs[job_id]
    if job["status"] == "running":
        return {"status": "running"}
    if job["status"] == "error":
        return {"status": "error", "error": job.get("error", "unknown")}
    return {"status": "done", "total": len(job["result"]), "responses": job["result"]}
