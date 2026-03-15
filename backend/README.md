# HabitFlow AI — Backend

FastAPI backend with 55+ endpoints, Claude AI integration, gamification engine, and push notifications.

## Quick Start

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in your credentials in .env
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

## Docker

```bash
docker build -t habitflow-api .
docker run -p 8000:8000 --env-file .env habitflow-api
```

## Database Migrations

Run these in your Supabase SQL Editor (in order):

1. `migrations/001_schema.sql` — Core tables, RLS, badges
2. `migrations/002_notifications.sql` — Push tokens, preferences

## Notification Scheduler

Run as a separate process for background notification delivery:

```bash
python -m app.services.scheduler
```

## Testing

```bash
pip install pytest pytest-asyncio httpx
pytest tests/ -v
```
