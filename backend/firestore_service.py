from __future__ import annotations

import uuid
from datetime import datetime, timezone

from firebase_admin import firestore

_db = None


def _client():
    global _db
    if _db is None:
        _db = firestore.client()
    return _db


def get_or_create_user(uid: str, email: str) -> None:
    """Create users/{uid} doc if it doesn't exist; never overwrites gating fields."""
    ref = _client().collection("users").document(uid)
    doc = ref.get()
    if doc.exists:
        ref.update({"email": email})
    else:
        ref.set(
            {
                "email": email,
                "free_used": False,
                "paid": False,
                "paid_at": None,
            }
        )


def can_run_pipeline(uid: str) -> bool:
    """Return True if the user may start a pipeline run."""
    doc = _client().collection("users").document(uid).get()
    if not doc.exists:
        return True  # no record yet — treat as a fresh user
    data = doc.to_dict()
    return data.get("paid", False) or not data.get("free_used", False)


def consume_free_use(uid: str) -> None:
    """Set free_used=True; no-op if the user is already paid."""
    ref = _client().collection("users").document(uid)
    doc = ref.get()
    if doc.exists and doc.to_dict().get("paid", False):
        return
    ref.update({"free_used": True})



def get_user_status(uid: str) -> dict[str, bool]:
    """Return the user's free_used and paid flags."""
    doc = _client().collection("users").document(uid).get()
    if not doc.exists:
        return {"free_used": False, "paid": False}
    data = doc.to_dict()
    return {"free_used": data.get("free_used", False), "paid": data.get("paid", False)}


# ---------------------------------------------------------------------------
# Pipeline persistence
# ---------------------------------------------------------------------------


def create_pipeline(
    uid: str | None,
    form_url: str,
    form_title: str,
    total_responses: int,
    base_name: str,
) -> str | None:
    """Create a pipeline doc; returns pipeline_id or None when uid is None."""
    if uid is None:
        return None
    pipeline_id = str(uuid.uuid4())
    _client().collection("pipelines").document(pipeline_id).set(
        {
            "user_uid": uid,
            "form_url": form_url,
            "form_title": form_title,
            "base_name": base_name,
            "total_responses": total_responses,
            "status": "in_progress",
            "created_at": datetime.now(tz=timezone.utc),
            "completed_at": None,
            "error": None,
        }
    )
    return pipeline_id


def save_pipeline_step(pipeline_id: str | None, step_key: str, data: object) -> None:
    """Persist a step's output JSON to the pipeline document."""
    if pipeline_id is None:
        return
    _client().collection("pipelines").document(pipeline_id).update(
        {f"step_{step_key}": data}
    )


def complete_pipeline(pipeline_id: str | None) -> None:
    """Mark pipeline as completed."""
    if pipeline_id is None:
        return
    _client().collection("pipelines").document(pipeline_id).update(
        {
            "status": "completed",
            "completed_at": datetime.now(tz=timezone.utc),
        }
    )


def fail_pipeline(pipeline_id: str | None, error: str) -> None:
    """Mark pipeline as failed with an error message."""
    if pipeline_id is None:
        return
    _client().collection("pipelines").document(pipeline_id).update(
        {"status": "failed", "error": error}
    )


def get_user_pipelines(uid: str, limit: int = 20) -> list[dict]:
    """Return metadata list for a user's pipelines (no step_* fields)."""
    docs = (
        _client()
        .collection("pipelines")
        .where("user_uid", "==", uid)
        .order_by("created_at", direction="DESCENDING")
        .limit(limit)
        .select(
            [
                "user_uid",
                "form_url",
                "form_title",
                "base_name",
                "total_responses",
                "status",
                "created_at",
                "completed_at",
                "error",
            ]
        )
        .stream()
    )
    result: list[dict] = []
    for doc in docs:
        d = doc.to_dict()
        if d is None:
            continue
        d["pipeline_id"] = doc.id
        result.append(d)
    return result


def get_pipeline(pipeline_id: str, uid: str) -> dict | None:
    """Return the full pipeline doc (including step_* fields) for the given uid."""
    doc = _client().collection("pipelines").document(pipeline_id).get()
    if not doc.exists:
        return None
    d = doc.to_dict()
    if d is None or d.get("user_uid") != uid:
        return None
    d["pipeline_id"] = doc.id
    return d
