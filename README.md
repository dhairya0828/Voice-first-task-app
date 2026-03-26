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

## Deployment (Public) - Recommended: Netlify + Oracle Cloud VM + Supabase/Neon

Use this architecture:

- Netlify: frontend hosting
- Oracle Cloud VM (Always Free): backend hosting (no sleep)
- Supabase/Neon: managed Postgres

### Files added for Oracle deployment

- `Dockerfile`
- `deployment/oracle/docker-compose.yml`
- `deployment/oracle/Caddyfile`
- `deployment/oracle/.env.oracle.example`
- `scripts/oracle/deploy.sh`

### Step A: Prepare database

Create Postgres on Supabase or Neon and keep a SQLAlchemy URL:

```text
postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require
```

### Step B: Prepare Oracle VM

1. Create an Ubuntu VM in Oracle Cloud (Always Free shape).
2. Open inbound ports in Oracle security rules:
   - `22` (SSH)
   - `80` (HTTP)
   - `443` (HTTPS)
3. Point a domain/subdomain (example `api.yourdomain.com`) to VM public IP with an `A` record.

### Step C: Install Docker on Oracle VM

SSH into VM and run:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

Log out and SSH again so docker group applies.

### Step D: Deploy backend containers

```bash
git clone <your-repo-url>
cd voice_task_app
cp deployment/oracle/.env.oracle.example deployment/oracle/.env.oracle
```

Edit `deployment/oracle/.env.oracle`:

- `API_DOMAIN=api.yourdomain.com`
- `SECRET_KEY=<strong-random-value>`
- `DATABASE_URL=<your-postgresql+psycopg-url>`
- `CORS_ORIGINS=https://<your-netlify-site>.netlify.app`
- `SERVE_FRONTEND=false`

Deploy:

```bash
bash scripts/oracle/deploy.sh
```

Verify:

- `https://api.yourdomain.com/health` returns `{"status":"ok"}`

### Step E: Configure Netlify frontend

This repo includes Netlify build setup:

- `netlify.toml`
- `scripts/build_netlify.sh`

In Netlify set:

- `NETLIFY_API_BASE_URL=https://api.yourdomain.com`
- optional: `NETLIFY_APP_NAME=Voice-First Task App`

Then redeploy Netlify.

### Step F: Smoke test

1. Open Netlify URL.
2. Register and login.
3. Create and complete tasks by voice.
4. Verify analytics updates.

## Alternate Deployment - Netlify + Render

Render is simpler but free tier can cold-start/sleep.

Backend settings:

- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- `CORS_ORIGINS=https://<your-netlify-site>.netlify.app`
- `SERVE_FRONTEND=false`

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

- Set specific CORS origins (Netlify domain), not `*`.

## Useful Notes

- Due dates are stored in UTC.
- If mic is unavailable, typed command input still works.
- Frontend API base URL is configurable via `window.APP_CONFIG.API_BASE_URL`.
- `SERVE_FRONTEND=false` disables the embedded frontend on Render root (`/`) and keeps API endpoints active.
