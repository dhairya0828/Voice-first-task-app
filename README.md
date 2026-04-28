# Voice-First Task App (FastAPI)

Voice-driven task manager with authentication, full task lifecycle controls, and an analytics dashboard.
https://voice-first-task-app.onrender.com/

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

## Deployment (Public) - Render Only

Current recommended setup for this repo:

- Render hosts both frontend and backend from the same FastAPI service
- Supabase/Neon hosts Postgres

### Step A: Prepare database

Create Postgres on Supabase or Neon and use a SQLAlchemy URL:

```text
postgresql+psycopg://USER:PASSWORD@HOST/DBNAME?sslmode=require
```

Use pooler/session endpoints if direct endpoint connectivity fails from your host.

### Step B: Deploy service on Render

1. Create a new Web Service from this repo.
2. Configure build/start:
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Set environment variables:
   - `APP_NAME=Voice-First Task App`
   - `SECRET_KEY=<strong-random-value>`
   - `ACCESS_TOKEN_EXPIRE_MINUTES=120`
   - `DATABASE_URL=<your-postgresql+psycopg-url>`
   - `CORS_ORIGINS=https://<your-render-service>.onrender.com`
   - `SERVE_FRONTEND=true`
   - `PYTHON_VERSION=3.12.8`
4. Optional but recommended:
   - Health check path: `/health`

### Step C: Smoke test

1. Open `https://<your-render-service>.onrender.com`.
2. Register and login.
3. Create and complete tasks by voice.
4. Verify analytics updates.

### Step D: Reduce cold-start impact

On Render free tier, idle instances can sleep. Keep a monitor (for example UptimeRobot) pinging:

`https://<your-render-service>.onrender.com/health`

## Environment Variables

Local `.env` example:

```env
APP_NAME="Voice-First Task App"
SECRET_KEY="replace-this"
ACCESS_TOKEN_EXPIRE_MINUTES=120
DATABASE_URL="sqlite:///./voice_tasks.db"
CORS_ORIGINS="*"
SERVE_FRONTEND=true
```

Production recommendation:

- Set specific CORS origins (your deployed frontend domain), not `*`.

## Useful Notes

- Due dates are stored in UTC.
- If mic is unavailable, typed command input still works.
- `SERVE_FRONTEND=true` serves frontend and backend from the same Render service.
- Docker + Oracle deployment assets remain in `deployment/oracle/` for future infra branches.
