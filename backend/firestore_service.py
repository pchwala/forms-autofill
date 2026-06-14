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
    """Create users/{uid} doc if it doesn't exist; never overwrites the credits balance."""
    ref = _client().collection("users").document(uid)
    doc = ref.get()
    if doc.exists:
        if email:
            ref.update({"email": email})
    else:
        ref.set(
            {
                "email": email,
                "credits": 0,
            }
        )


def get_credits(uid: str) -> int:
    """Return the user's current credit balance (0 if no record)."""
    doc = _client().collection("users").document(uid).get()
    if not doc.exists:
        return 0
    return int(doc.to_dict().get("credits", 0))


def add_credits(uid: str, n: int, idempotency_key: str | None = None) -> int:
    """Add n credits to the user (creating the field if missing); return the new balance.

    Used by the Stripe webhook + confirm endpoints. When ``idempotency_key`` is given
    (e.g. a Stripe Checkout session id), the grant is recorded in
    ``credit_grants/{idempotency_key}`` inside the same transaction; a repeated call with
    the same key is a no-op that returns the already-credited balance. This makes webhook
    retries and the on-return confirm call safe to run more than once.
    """
    user_ref = _client().collection("users").document(uid)
    grant_ref = (
        _client().collection("credit_grants").document(idempotency_key)
        if idempotency_key
        else None
    )

    @firestore.transactional
    def _txn(transaction) -> int:
        # Reads must precede writes within a Firestore transaction.
        user_snapshot = user_ref.get(transaction=transaction)
        if grant_ref is not None:
            grant_snapshot = grant_ref.get(transaction=transaction)
            if grant_snapshot.exists:
                return int(grant_snapshot.to_dict().get("new_balance", 0))

        current = int(user_snapshot.to_dict().get("credits", 0)) if user_snapshot.exists else 0
        new_balance = current + n
        transaction.set(user_ref, {"credits": new_balance}, merge=True)
        if grant_ref is not None:
            transaction.set(
                grant_ref,
                {
                    "uid": uid,
                    "amount": n,
                    "new_balance": new_balance,
                    "granted_at": datetime.now(tz=timezone.utc),
                },
            )
        return new_balance

    return _txn(_client().transaction())


def consume_credits(uid: str, n: int) -> int:
    """Atomically deduct up to n credits; return the number actually deducted.

    Charging happens after a submit run, so n is the count of responses that confirmed
    (already pre-checked to be <= balance). Deducting ``min(current, n)`` guards against a
    balance that changed between the pre-check and the charge.
    """
    if n <= 0:
        return 0
    ref = _client().collection("users").document(uid)

    @firestore.transactional
    def _txn(transaction) -> int:
        snapshot = ref.get(transaction=transaction)
        current = int(snapshot.to_dict().get("credits", 0)) if snapshot.exists else 0
        deducted = min(current, n)
        if deducted > 0:
            transaction.update(ref, {"credits": current - deducted})
        return deducted

    return _txn(_client().transaction())


def get_user_status(uid: str) -> dict[str, int]:
    """Return the user's credit balance."""
    return {"credits": get_credits(uid)}


# ---------------------------------------------------------------------------
# Pipeline persistence
# ---------------------------------------------------------------------------


def create_pipeline(
    pipeline_id: str,
    uid: str | None,
    form_url: str,
    form_title: str,
    total_responses: int,
    base_name: str,
    desire_prompt: str | None = None,
) -> str | None:
    """Create a pipeline doc under the given id; returns the id or None when uid is None.

    The caller mints the id up front so the Firestore doc id is the same id the client holds
    (one id end-to-end — no separate in-memory key).
    """
    if uid is None:
        return None
    _client().collection("pipelines").document(pipeline_id).set(
        {
            "user_uid": uid,
            "form_url": form_url,
            "form_title": form_title,
            "base_name": base_name,
            "total_responses": total_responses,
            "desire_prompt": desire_prompt,
            "preview": None,
            "selected_persona_codes": None,
            "status": "in_progress",
            "created_at": datetime.now(tz=timezone.utc),
            "completed_at": None,
            "error": None,
        }
    )
    return pipeline_id


def update_pipeline(pipeline_id: str | None, fields: dict) -> None:
    """Patch arbitrary top-level fields on a pipeline document."""
    if pipeline_id is None:
        return
    _client().collection("pipelines").document(pipeline_id).update(fields)


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
