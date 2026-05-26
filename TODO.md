## Plan: Usage Gating + Ko-fi Payment Integration

**Goal**: Each authenticated user gets one free pipeline run. After that, a one-time Ko-fi payment of €5+ (any currency) unlocks unlimited access. User links their payment by writing their Google account email in the Ko-fi donation message.

### Decisions
- 1 use = pipeline fully completes (step 5 submits responses), either mode
- After payment: unlimited forever (one-time)
- Ko-fi → user linking: user writes their Firebase/Google email in the Ko-fi payment message
- Database: Firestore (firebase-admin already integrated — no new infra)
- Minimum payment: €5, any currency — trust equivalent amounts, no strict currency check
- Email typos in Ko-fi message: handle manually as needed (low traffic)
- `free_used` marked at pipeline START (before dispatch), not on completion — prevents concurrent abuse
- `/webhook/kofi` is unauthenticated (Ko-fi can't send Firebase tokens); secured by `verification_token` check
- Firestore Security Rules: deny all client-side access to `users` collection — backend only

### Firestore Schema
Collection: `users`, Document ID = Firebase UI
{
email: string,
free_used: boolean, // true = 1 free run consumed
paid: boolean, // true = paid ≥€5 via Ko-fi
paid_at: timestamp | null,
kofi_email: string | null // email extracted from Ko-fi message
}

### Ko-fi Webhook Flow
Ko-fi POSTs to `/webhook/kofi` with a `data` form field (URL-encoded JSON):
1. Verify `verification_token` == `KOFI_VERIFICATION_TOKEN` env var → 403 if mismatch
2. Check `float(amount) >= 5.0` → silent 200 ignore if below threshold
3. Regex-extract email from `message` field → silent ignore if no email found
4. `firebase_admin.auth.get_user_by_email(email)` → silent ignore if user not found
5. Firestore: set `paid=True`, `paid_at=now`, `kofi_email=extracted_email`

---

### Phase 1 — Firestore Setup
- [x] Create `backend/firestore_service.py` with:
  - `get_or_create_user(uid, email)` — upserts `users/{uid}` doc
  - `can_run_pipeline(uid) -> bool` — `True` if `paid` or `free_used == False`
  - `consume_free_use(uid)` — sets `free_used = True` (skip if already paid)
  - `mark_paid(uid, kofi_email, amount)` — sets `paid=True`, `paid_at=now`
- [x] Initialize Firestore in `backend/main.py` via `firebase_admin.firestore.client()` (reuses existing firebase-admin init)
- [x] Add `KOFI_VERIFICATION_TOKEN` env var to backend config/docs

### Phase 2 — Backend Usage Gating *(depends on Phase 1)*
- [x] Refactor `_verify(authorization)` in `backend/main.py` to return `{"uid": ..., "email": ...}` instead of None
- [x] Update all 6 existing endpoints to capture returned dict and call `get_or_create_user(uid, email)`
- [x] In `POST /run` and `POST /session`: call `can_run_pipeline(uid)` → raise `HTTPException(402)` if blocked, then call `consume_free_use(uid)` before dispatching background thread

### Phase 3 — Ko-fi Webhook Endpoint *(parallel with Phase 2)*
- [x] Add `POST /webhook/kofi` to `backend/main.py` (no auth):
  - Parse `data` form field (URL-encoded JSON)
  - Verify `verification_token`, check amount, extract email from message, look up Firebase user, call `mark_paid()`

### Phase 4 — User Status Endpoint *(depends on Phase 2)*
- [x] Add `GET /user/status` to `backend/main.py` (authenticated):
  - Returns `{ "free_used": bool, "paid": bool }`

### Phase 5 — Frontend Payment Wall *(depends on Phase 4)*
- [x] Create `frontend/src/hooks/useUserStatus.ts` — fetches `/user/status` using `getToken()` pattern from `useAuth.ts`, returns `{ freeUsed, paid, loading }`
- [x] Modify `frontend/src/components/InputForm.tsx` — if `freeUsed && !paid`, replace form with payment wall: "You've used your free run. Donate €5+ on Ko-fi and write your Google account email in the payment message."
- [x] Modify `frontend/src/hooks/usePipeline.ts` — if `/run` or `/session` returns 402, surface a `blocked` state

### Verification
- [ ] Fresh user: first pipeline run proceeds, `free_used` flips to `true` in Firestore
- [ ] `free_used=true` + `paid=false`: `POST /run` returns 402, frontend shows payment wall
- [ ] Simulate valid Ko-fi webhook (correct token, €5, email in message) → `paid=true` in Firestore, user can run again
- [ ] Simulate webhook with wrong `verification_token` → 403
- [ ] Simulate webhook with amount `4.99` → silent 200, no Firestore write
- [ ] Simulate webhook with unknown email → silent 200, no Firestore write

### Files to modify
- `backend/main.py` — `_verify()` refactor, gating in `/run`+`/session`, new `/webhook/kofi`, new `/user/status`
- NEW `backend/firestore_service.py` — all Firestore CRUD
- `backend/requirements.txt` — verify `google-cloud-firestore` present (likely via firebase-admin)
- NEW `frontend/src/hooks/useUserStatus.ts` — user status fetching
- `frontend/src/components/InputForm.tsx` — payment wall UI
- `frontend/src/hooks/usePipeline.ts` — 402 handling

### Notes
- Firestore Security Rules must deny all client-side access to `users` collection (configure in Firebase console)
- Consider a manual admin endpoint `POST /admin/grant-paid?email=...` later if email typo issues grow
