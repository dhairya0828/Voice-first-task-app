# Voice-First Task App (FastAPI)

Voice-driven task manager with authentication, full task lifecycle controls, and an analytics dashboard.

## Features

- Voice command interpretation into structured actions (`create`, `complete`, `cancel`, `delay`)
- Manual task creation/edit actions as fallback
- JWT-based authentication
- Analytics dashboard:
  - tasks completed on time
  - tasks pending
  - tasks delayed
  - status distribution and completion trend graphs
- Ambiguity handling with confidence score + warnings before execute

## Tech Stack

- Backend: FastAPI, SQLAlchemy, JWT, dateparser
- Frontend: HTML/CSS/Vanilla JS + Canvas charts
- Database:
  - Local: SQLite
  - Production: Postgres (Neon/Supabase compatible)

## Run Locally

### 1) Prerequisites

- Python 3.10+ recommended
- `pip`

### 2) Setup

```bash
cd voice_task_app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set a strong `SECRET_KEY`.

### 3) Start app

```bash
uvicorn app.main:app --reload
```

Open: [http://127.0.0.1:8000](http://127.0.0.1:8000)

### 4) Run tests

```bash
PYTHONPATH=. pytest
```

## Deployment (Public) - Netlify + Render + Neon

Use this architecture:

- Netlify: frontend hosting
- Render: FastAPI backend hosting
- Neon: free hosted Postgres

### Step A: Create free Postgres (Neon)

1. Create a Neon project and database.
2. Copy connection string.
3. Convert it to SQLAlchemy `psycopg` format:

```text
postgresql+psycopg://USER:PASSWORD@HOST/DBNAME?sslmode=require
```

### Step B: Deploy backend (Render)

1. Create a new **Web Service** from this repo.
2. Configure:
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Add environment variables:
   - `APP_NAME=Voice-First Task App`
   - `SECRET_KEY=<strong-random-value>`
   - `ACCESS_TOKEN_EXPIRE_MINUTES=120`
   - `DATABASE_URL=<your-postgresql+psycopg URL>`
   - `CORS_ORIGINS=https://<your-netlify-site>.netlify.app`
4. Deploy and confirm health:
   - `https://<your-render-service>.onrender.com/health`

### Step C: Deploy frontend (Netlify)

This repo includes:

- `netlify.toml` (build + publish settings)
- `scripts/build_netlify.sh` (generates static site into `netlify_site/`)

In Netlify:

1. Import the GitHub repo.
2. Set environment variable:
   - `NETLIFY_API_BASE_URL=https://<your-render-service>.onrender.com`
3. Deploy (Netlify reads `netlify.toml` automatically).

Optional:

- `NETLIFY_APP_NAME=Voice-First Task App`

### Step D: Smoke test deployed app

1. Open Netlify URL.
2. Register and login.
3. Create task by voice command.
4. Execute complete/cancel/delay.
5. Verify dashboard updates.

## Environment Variables

Local `.env` example:

```env
APP_NAME="Voice-First Task App"
SECRET_KEY="replace-this"
ACCESS_TOKEN_EXPIRE_MINUTES=120
DATABASE_URL="sqlite:///./voice_tasks.db"
CORS_ORIGINS="*"
```

Production recommendation:

- Set specific CORS origins (Netlify domain), not `*`.

## Useful Notes

- Due dates are stored in UTC.
- If mic is unavailable, typed command input still works.
- Frontend API base URL is configurable via `window.APP_CONFIG.API_BASE_URL`.
