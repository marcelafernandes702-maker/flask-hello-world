# LEBS Stumble Backend

Test backend for Stumble Guys 0.50 using FastAPI.

## Project structure

```text
LEBS_STUMBLE_BACKEND/
├── main.py
├── requirements.txt
└── README.md
```

## Requirements

The project uses Python 3.10 or newer and the dependencies listed in `requirements.txt`:

```text
fastapi>=0.115,<1.0
uvicorn[standard]>=0.30,<1.0
pydantic>=2.0,<3.0
```

Install them with:

```bash
pip install -r requirements.txt
```

## Run locally

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Interactive API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

## Published backend

```text
https://sglend-backend.onrender.com
```

## Main routes

```text
GET  /
GET  /bootstrap
GET  /api/bootstrap
GET  /config
GET  /api/config
GET  /api/photon/config
POST /user/login
POST /api/user/login
POST /api/v1/user/login
POST /user/inventory/selection
POST /api/user/inventory/selection
POST /api/v1/user/inventory/selection
```

## Photon configuration

The backend advertises the following Photon Realtime configuration:

```json
{
  "enabled": true,
  "appId": "6fe8305a-ef22-40f2-9c0e-3052a8adec0d",
  "region": "sa",
  "regions": "sa;us;usw;eu"
}
```

The backend only publishes this configuration. The actual Photon connection is opened by the game client, and the Photon application must be active in the Photon dashboard.

## Render deployment

Set the Render service root directory to the directory containing `main.py` and `requirements.txt`.

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Do not use `uvicorn app:app` unless the Python file is named `app.py`. This project uses `main.py`, so the correct command is `uvicorn main:app`.

## Important note

The backend uses an in-memory test database. Users and access tokens are lost whenever the service restarts. This backend does not implement a Photon server; Photon Realtime remains a separate service.

