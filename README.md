# Forms Autofill

An AI-powered tool that automatically fills Google Forms with realistic, randomized responses. It extracts form fields, generates a response strategy via OpenAI, synthesizes answers, and submits them via requests.

## Architecture

- **Backend** — FastAPI (Python 3.12), OpenAI API, Firebase Admin (auth)
- **Frontend** — React 19 + Vite, Material UI, Firebase Auth (Google Sign-In)

## Prerequisites

- Python 3.12+
- Node.js 18+
- An [OpenAI API key](https://platform.openai.com/api-keys)
- A Firebase project *(optional — can be bypassed in local dev)*

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
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### Configure environment

Create `backend/.env` (copy from the example):

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and set your OpenAI key and Firebase credentials:

```dotenv
# Your OpenAI API key
OPENAI_API_KEY=sk-...

# Allow requests from the Vite dev server
CORS_ORIGINS=http://localhost:5173

# Firebase Admin credentials — file path or raw JSON
FIREBASE_CREDENTIALS_JSON=./firebase_credentials.json
```

> **Firebase credentials** (`FIREBASE_CREDENTIALS_JSON`) are required — auth is always enabled, including in local dev.

#### Run the backend

```bash
# From the project root
uvicorn backend.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

---

### 3. Frontend

#### Install Node dependencies

```bash
cd frontend
npm install
```

#### Configure environment

Create `frontend/.env.development` (copy from the example):

```bash
cp frontend/.env.example frontend/.env.development
```

Edit `frontend/.env.development`:

```dotenv
# Backend URL
VITE_API_URL=http://localhost:8000

# Firebase config (required — auth is always enabled)
VITE_FIREBASE_API_KEY=
VITE_FIREBASE_AUTH_DOMAIN=
VITE_FIREBASE_PROJECT_ID=
VITE_FIREBASE_APP_ID=
```

#### Run the frontend

```bash
npm run dev
```

The app will be available at `http://localhost:5173`.

---

## Pipeline Overview

| Step | Description |
|------|-------------|
| 1 | **Extract** — scrapes Google Form fields and options |
| 2 | **Strategy** — uses OpenAI to generate a plausible respondent profile |
| 3 | **Generate** — produces answer sets from the strategy |
| 4 | **Shuffle** — randomises response order |
| 5 | **Submit** — submits each response via requests |

---

## Docker (Backend)

```bash
docker build -t forms-autofill-backend ./backend
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  -e FIREBASE_CREDENTIALS_JSON="$(cat backend/firebase_credentials.json)" \
  forms-autofill-backend
```
