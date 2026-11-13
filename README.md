# Stumble Tracer 0.50 Backend

FastAPI backend for testing version 0.50 lobby entry. It implements guest login, persistent profiles, user settings, inventory selection, shared data, lobby, servers, tournaments and compatible JSON responses.

## Files

- `main.py` — FastAPI application.
- `requirements.txt` — Python dependencies.
- `data/users.json` — created automatically to persist player profiles.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000











