# Stumble Pool 0.50 Backend

Reference FastAPI backend for testing version 0.50 lobby entry. It implements the routes observed in the client flow, including guest login, `usersettings`, inventory selection, shared data, persistent profiles, lobby, servers, tournaments, and compatible JSON responses.

## Files

- `main.py` — FastAPI application.
- `requirements.txt` — Python dependencies.
- `data/users.json` — created automatically on first run to persist player profiles.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000









