from __future__ import annotations

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
                "kofi_email": None,
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


def mark_paid(uid: str, kofi_email: str, amount: float) -> None:
    """Record a successful Ko-fi payment."""
    _client().collection("users").document(uid).update(
        {
            "paid": True,
            "paid_at": datetime.now(tz=timezone.utc),
            "kofi_email": kofi_email,
        }
    )


def get_user_status(uid: str) -> dict[str, bool]:
    """Return the user's free_used and paid flags."""
    doc = _client().collection("users").document(uid).get()
    if not doc.exists:
        return {"free_used": False, "paid": False}
    data = doc.to_dict()
    return {"free_used": data.get("free_used", False), "paid": data.get("paid", False)}
