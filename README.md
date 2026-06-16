# Forms Autofill

An AI-powered tool that automatically fills Google Forms with realistic, randomised responses. Targeted at Polish-speaking users. Anyone can use the site anonymously — a free preview shows the generated respondent personas and predicted answer distributions before any credits are spent.

## Architecture

- **Backend** — FastAPI (Python 3.12), OpenAI API, Firebase Admin (auth + Firestore)
- **Frontend** — React 19 + Vite, Material UI (dark theme), Firebase Auth (anonymous + Google Sign-In), Polish UI

## Product flow

| Phase | Steps | Cost |
|-------|-------|------|
| **Preview** (free) | 1 Extract form · 2 Generate strategy | Free |
| **Submit** (paid) | 3 Generate responses · 4 Shuffle · 5 Submit | 1 credit per submitted response |

You can bypass payment by changing credits in Firestore. I am working on making the project able to run fully local.
Users can review generated personas and predicted answer distributions before committing any credits.

## Prerequisites

- Python 3.12+
- Node.js 18+
- An [OpenAI API key](https://platform.openai.com/api-keys)
- A Firebase project with **Anonymous Auth** and **Google Sign-In** enabled, and a Firestore database *(required — auth and credits are always on)*

---

## Local Development Setup

### 1. Clone the repo

```bash
git clone <repo-url>
cd forms-autofill
```

---

### 2. Backend

#### Install Python dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

#### Configure environment

Create `backend/.env`:

```dotenv
# Required
OPENAI_API_KEY=sk-...
FIREBASE_CREDENTIALS_JSON=./backend/firebase_credentials.json

# Optional
CORS_ORIGINS=http://localhost:5173
```

`FIREBASE_CREDENTIALS_JSON` accepts either a file path to your service account JSON or the raw JSON string itself. Download the service account key from **Firebase Console → Project Settings → Service Accounts**.

#### Run the backend

```bash
# From the project root (backend is a package)
uvicorn backend.main:app --reload --port 8000
```

API available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

---

### 3. Frontend

#### Install Node dependencies

```bash
cd frontend
npm install
```

#### Configure environment

Create `frontend/.env.development`:

```dotenv
VITE_API_URL=http://localhost:8000

# Firebase web app config (from Firebase Console → Project Settings → Your apps)
VITE_FIREBASE_API_KEY=
VITE_FIREBASE_AUTH_DOMAIN=
VITE_FIREBASE_PROJECT_ID=
VITE_FIREBASE_APP_ID=
```

#### Run the frontend

```bash
npm run dev
```

App available at `http://localhost:5173`.

---

## Firebase setup checklist

1. Create a Firebase project at [console.firebase.google.com](https://console.firebase.google.com).
2. **Authentication → Sign-in method**: enable **Anonymous** and **Google**.
3. **Firestore Database**: create a database (start in production mode is fine).
4. **Project Settings → Service Accounts**: generate a new private key and save it as `backend/firebase_credentials.json` (gitignored).
5. **Project Settings → Your apps**: add a Web app and copy the config into `frontend/.env.development`.

---

## Docker (Backend)

```bash
docker build -t forms-autofill-backend ./backend
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  -e FIREBASE_CREDENTIALS_JSON="$(cat backend/firebase_credentials.json)" \
  forms-autofill-backend
```
