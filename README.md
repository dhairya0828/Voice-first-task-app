# Voice-First Task App (FastAPI)

A complete implementation of **Voice-First Task App** with:
- Voice command interpretation from natural language
- Task lifecycle actions (create, complete, cancel, delay)
- User authentication
- Analytics dashboard with visual graphs

## Requirement Mapping

### 1) Voice input with structured task extraction
Implemented via:
- Browser mic capture (`Web Speech API`) in the frontend
- Backend NLP parser (`app/services/voice_parser.py`) extracting:
  - `title`
  - `description`
  - `due_date`
  - command `action`

### 2) Task actions
Supported actions:
- `create`
- `complete`
- `cancel`
- `delay`

You can do these by voice (`/api/voice/execute`) or manually from the UI.

### 3) Authentication
Implemented with:
- Register: `POST /api/auth/register`
- Login: `POST /api/auth/login` (JWT)
- Profile: `GET /api/auth/me`

### 4) Analytics dashboard with graphs
Implemented in UI + API:
- `Tasks completed on time`
- `Tasks currently pending`
- `Tasks that were delayed`
- Extra KPIs: completed late, cancelled
- Visual graphs:
  - Status distribution bar chart
  - Completion trend line chart (last 14 days)

## Cherry-On-Top Features Included

- Ambiguity handling with confidence score and warnings before execution
- Voice action automation (`complete/cancel/delay`) with fuzzy task matching
- Task event history model (`task_events`) for auditability
- Manual fallback UI (important when mic/browser support is unavailable)

## Tech Stack

- Backend: `FastAPI`, `SQLAlchemy`, `SQLite`, `JWT`
- Frontend: Server-rendered HTML + Vanilla JS + Canvas charts
- NLP/date extraction: `dateparser`

## Project Structure

```text
voice_task_app/
  app/
    main.py
    config.py
    database.py
    models.py
    schemas.py
    security.py
    dependencies.py
    routers/
      auth.py
      tasks.py
      voice.py
      analytics.py
    services/
      auth.py
      task_service.py
      voice_parser.py
      analytics.py
    static/
      app.js
      styles.css
    templates/
      index.html
  tests/
    test_voice_parser.py
  requirements.txt
  .env.example
```

## How To Run (Beginner-Friendly)

Run these commands from terminal.

### 0) Prerequisites
- Python `3.9+`
- `pip`

### 1) Open project folder
```bash
cd /path/voice_task_app
```

### 2) Create virtual environment
```bash
python3 -m venv .venv
```

### 3) Activate virtual environment
macOS/Linux:
```bash
source .venv/bin/activate
```

Windows (PowerShell):
```powershell
.\.venv\Scripts\Activate.ps1
```

### 4) Install dependencies
```bash
pip install -r requirements.txt
```

### 5) Create `.env`
```bash
cp .env.example .env
```

Then edit `.env` and set a strong `SECRET_KEY`.

### 6) Start the app
```bash
uvicorn app.main:app --reload
```

### 7) Open in browser
Go to:
- [http://127.0.0.1:8000](http://127.0.0.1:8000)

## First Demo Flow

1. Register a user.
2. Login.
3. Use voice command:
   - `Remind me to submit the quarterly report by next Friday`
4. Click **Interpret** (review confidence/warnings).
5. Click **Execute**.
6. Complete/cancel/delay tasks and watch dashboard update.

## Testing

Run parser tests:
```bash
PYTHONPATH=. pytest
```

## Important Notes

- Due dates are stored in UTC.
- If browser mic is unsupported, type command text manually in the voice box.
- Fuzzy matching is used for voice actions like complete/cancel/delay.

## Submission Checklist

- Ensure `.env` exists and app starts with `uvicorn app.main:app --reload`.
- Run tests with `PYTHONPATH=. pytest`.
- Include only project files in the final branch.
- Share:
  - Branch name
  - Repository URL
  - Run steps from this README
