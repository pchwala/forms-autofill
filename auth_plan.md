# Plan: Firebase Auth Integration

## Summary

Replace the static `API_KEY` auth with Firebase Google Sign-In. The backend verifies Firebase ID
tokens via `firebase-admin`. A single env flag (`AUTH_DISABLED` / `VITE_AUTH_DISABLED`) bypasses
all auth for dev/testing. No Firebase project yet — stub config placeholders throughout.

### Decisions
- **Google Sign-In only** (no email/password)
- **Firebase ID tokens fully replace** the static API key — no fallback key
- Firebase project not yet created — all `VITE_FIREBASE_*` and `FIREBASE_CREDENTIALS_JSON` values are stubs
- `VITE_AUTH_DISABLED=true` is pre-set in `frontend/.env` so the current dev workflow is unaffected until a real project is wired up

---

## Phase 1 — Backend

### Step 1 — Add firebase-admin dependency
- `backend/requirements.txt`: add `firebase-admin`

### Step 2 — Firebase Admin init + AUTH_DISABLED flag in `main.py`
- Add `AUTH_DISABLED = os.getenv("AUTH_DISABLED", "false").lower() == "true"` near top
- At module level, init Firebase Admin SDK only when not disabled:
  - Read `FIREBASE_CREDENTIALS_JSON` env var (a JSON string of the service account key)
  - If present, use `firebase_admin.credentials.Certificate(json.loads(creds_json))`
  - If absent, fall back to `firebase_admin.credentials.ApplicationDefault()`
  - Call `firebase_admin.initialize_app(cred)`

### Step 3 — Replace `_verify()` with Firebase token check
- Old signature: `_verify(key: str) -> None`
- New signature: `_verify(authorization: str) -> None`
  - If `AUTH_DISABLED`: return immediately (no-op)
  - Parse `Bearer <token>` from the `authorization` header value
  - Call `firebase_admin.auth.verify_id_token(token)`
  - Wrap in try/except → raise `HTTPException(401)` on any failure

### Step 4 — Update all route signatures
- Replace `x_api_key: str = Header(...)` with `authorization: str = Header(...)` in all 6 routes:
  `POST /run`, `POST /session`, `GET /session/{id}`, `POST /session/{id}/advance`,
  `GET /stream/{id}`, `GET /result/{id}`
- Pass `authorization` to `_verify(authorization)` in each handler
- CORS `allow_headers=["*"]` already covers the `Authorization` header — no change needed

### Step 5 — Backend env stubs
- `backend/Dockerfile`: add stub `ENV` lines for `AUTH_DISABLED` and `FIREBASE_CREDENTIALS_JSON`
- For local dev: set `AUTH_DISABLED=true` in a `.env` file at the repo root

---

## Phase 2 — Frontend

### Step 6 — Install firebase package
```
cd frontend && npm install firebase
```

### Step 7 — Create `frontend/src/firebase.ts` (new file)
- Initialize a Firebase App from `VITE_FIREBASE_API_KEY`, `VITE_FIREBASE_AUTH_DOMAIN`,
  `VITE_FIREBASE_PROJECT_ID`, `VITE_FIREBASE_APP_ID`
- Export `auth` (`getAuth(app)`) and `googleProvider` (`new GoogleAuthProvider()`)
- If `VITE_AUTH_DISABLED=true`, export stubs so the rest of the code compiles without a real project

### Step 8 — Create `frontend/src/hooks/useAuth.ts` (new file)
- Subscribe to `onAuthStateChanged(auth, ...)` to track `user: User | null`
- Expose:
  - `user` — current Firebase User or null
  - `loading` — true until first auth state event fires
  - `signIn()` — calls `signInWithPopup(auth, googleProvider)`
  - `signOut()` — calls `signOut(auth)`
  - `getToken(): Promise<string>` — returns `user.getIdToken()`, or `""` when `VITE_AUTH_DISABLED=true`

### Step 9 — Create `frontend/src/components/AuthGuard.tsx` (new file)
- Reads `VITE_AUTH_DISABLED` env var
- If disabled → renders `children` directly (no login wall)
- If loading → shows MUI `CircularProgress` spinner
- If no user → shows centered MUI "Sign in with Google" button
- If signed in → renders `children` plus a small sign-out button (e.g. in a top-right corner)

### Step 10 — Update `frontend/src/hooks/usePipeline.ts`
- Change hook signature to `usePipeline(getToken: () => Promise<string>)`
- Remove the module-level `const API_KEY = ...` and the static `authHeaders()` function
- Add a local async helper `buildHeaders(getToken)`:
  - Awaits `getToken()`
  - Returns `{ Authorization: "Bearer <token>", "Content-Type": "application/json" }`
  - Omits the `Authorization` key entirely when the token is an empty string (dev mode)
- Await `buildHeaders(getToken)` in `startFullPipeline`, `createSession`, `advanceSession`,
  and in the `fetch(…/stream/…)` call inside `openStream`

### Step 11 — Update `frontend/src/App.tsx`
- Import and call `useAuth()` at the component top
- Pass `getToken` from `useAuth` to `usePipeline(getToken)`
- Wrap the returned JSX in `<AuthGuard>`

### Step 12 — Env var stubs
`frontend/.env.example` — add:
```
VITE_FIREBASE_API_KEY=
VITE_FIREBASE_AUTH_DOMAIN=
VITE_FIREBASE_PROJECT_ID=
VITE_FIREBASE_APP_ID=
VITE_AUTH_DISABLED=false
```

`frontend/.env` (local dev, git-ignored) — add:
```
VITE_AUTH_DISABLED=true
```
This keeps the existing dev workflow unaffected until a real Firebase project is wired up.

---

## Files touched

| File | Change |
|---|---|
| `backend/requirements.txt` | Add `firebase-admin` |
| `backend/main.py` | Firebase init, new `_verify()`, update all 6 route signatures |
| `backend/Dockerfile` | Add env stub lines |
| `frontend/src/firebase.ts` | **NEW** — Firebase app + auth init |
| `frontend/src/hooks/useAuth.ts` | **NEW** — auth state hook |
| `frontend/src/components/AuthGuard.tsx` | **NEW** — login wall component |
| `frontend/src/hooks/usePipeline.ts` | Accept `getToken` param, async `buildHeaders` |
| `frontend/src/App.tsx` | Wire `useAuth` → `usePipeline`, wrap in `AuthGuard` |
| `frontend/.env` | Add `VITE_AUTH_DISABLED=true` |
| `frontend/.env.example` | Add all new `VITE_FIREBASE_*` stubs |

---

## Verification checklist

1. `AUTH_DISABLED=true` + `VITE_AUTH_DISABLED=true` → app loads with no login prompt, full pipeline runs as before
2. Auth enabled, no user → backend returns `401`; frontend shows Google sign-in screen
3. After Google sign-in → pipeline runs; requests carry `Authorization: Bearer <id-token>`
4. Token expiry → Firebase `getIdToken()` handles silent refresh automatically; confirm with a >1 h session
5. Run `uvicorn backend.main:app` and `npm run dev` to exercise both code paths
