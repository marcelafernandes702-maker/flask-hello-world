"""
Minimal REST backend for the Stumble Lend lobby.

Local run:
    pip install -r requirements.txt
    gunicorn app:app

Render start command:
    gunicorn app:app --access-logfile -

This server stores data in memory. For production, replace the dictionaries
with a database and set SECRET_KEY through an environment variable.
"""

from __future__ import annotations

import os
import secrets
import time
import uuid
from functools import wraps
from typing import Any, Dict, Optional

from flask import Flask, jsonify, request

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key")


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Auth-Token"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

SERVICE_NAME = "Stumble Lend"
SERVICE_VERSION = "0.50"
TOURNAMENTS = ["Lend BD 1v1", "Lend LD 1v1"]
REGIONS = [
    {"code": "asia", "name": "Asia", "location": "Singapore"},
    {"code": "au", "name": "Australia", "location": "Sydney"},
    {"code": "cae", "name": "Canada East", "location": "Montreal"},
    {"code": "cn", "name": "China Mainland", "location": "Shanghai"},
    {"code": "eu", "name": "Europe", "location": "Amsterdam"},
    {"code": "hk", "name": "Hong Kong", "location": "Hong Kong"},
    {"code": "in", "name": "India", "location": "Chennai"},
    {"code": "jp", "name": "Japan", "location": "Tokyo"},
    {"code": "za", "name": "South Africa", "location": "Johannesburg"},
    {"code": "sa", "name": "South America", "location": "Sao Paulo"},
    {"code": "kr", "name": "South Korea", "location": "Seoul"},
    {"code": "tr", "name": "Turkey", "location": "Istanbul"},
    {"code": "uae", "name": "United Arab Emirates", "location": "Dubai"},
    {"code": "us", "name": "USA East", "location": "Washington DC"},
    {"code": "usw", "name": "USA West", "location": "San Jose"},
    {"code": "ussc", "name": "USA South Central", "location": "Dallas"},
]
SERVER_URL = os.environ.get("PUBLIC_BASE_URL", "https://sglend-backend.onrender.com")

# Temporary in-memory storage. Data resets when the Render process restarts.
USERS: Dict[str, Dict[str, Any]] = {}
TOKENS: Dict[str, str] = {}
MATCHES: Dict[str, Dict[str, Any]] = {}


def now() -> int:
    return int(time.time())


def json_error(message: str, status: int = 400, code: str = "bad_request"):
    return jsonify({"ok": False, "error": code, "message": message}), status


def payload() -> Dict[str, Any]:
    data = request.get_json(silent=True)
    if isinstance(data, dict):
        return data
    return request.form.to_dict()


def get_token() -> Optional[str]:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return request.headers.get("X-Auth-Token") or request.args.get("token")


def current_user() -> Optional[Dict[str, Any]]:
    token = get_token()
    user_id = TOKENS.get(token or "")
    return USERS.get(user_id) if user_id else None


def auth_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            return json_error("authentication required", 401, "unauthorized")
        return fn(user, *args, **kwargs)

    return wrapped


def public_user(user: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": user["id"],
        "name": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "playerName": user["username"],
        "playername": user["username"],
        "serverNumber": user["username"].replace(".gg/sglend", ""),
        "tournamentsname": TOURNAMENTS[0],
        "tournamentsname2": TOURNAMENTS[1],
        "userId": user["id"],
        "username": user["username"],
        "displayName": user["username"],
        "trophies": user["trophies"],
        "crowns": user["crowns"],
        "coins": user["coins"],
        "gems": user["gems"],
        "createdAt": user["createdAt"],
    }


def login_response(user: Dict[str, Any], token: str):
    player = public_user(user)
    return {
        "ok": True,
        "success": True,
        "token": token,
        "accessToken": token,
        "sessionToken": token,
        "expiresIn": 60 * 60 * 24 * 30,
        "user": player,
        "player": player,
        "profile": player,
    }


@app.get("/")
def index():
    return jsonify(
        {
            "ok": True,
            "service": SERVICE_NAME,
            "game": SERVICE_NAME,
            "version": SERVICE_VERSION,
            "tournaments": TOURNAMENTS,
            "tournamentsname": TOURNAMENTS[0],
            "tournamentsname2": TOURNAMENTS[1],
            "status": "online",
            "health": f"{SERVER_URL}/health",
        }
    )


@app.get("/health")
@app.get("/healthz")
@app.get("/api/health")
def health():
    return jsonify({"ok": True, "status": "ok", "service": "sglend-backend", "timestamp": now()})


@app.get("/version")
@app.get("/api/version")
def version():
    return jsonify({"ok": True, "version": SERVICE_VERSION, "apiVersion": "v1"})


@app.get("/config")
@app.get("/api/config")
@app.get("/api/v1/config")
def config():
    return jsonify(
        {
            "ok": True,
            "name": SERVICE_NAME,
            "gameName": SERVICE_NAME,
            "version": SERVICE_VERSION,
            "tournaments": TOURNAMENTS,
            "tournamentsname": TOURNAMENTS[0],
            "tournamentsname2": TOURNAMENTS[1],
            "server": SERVER_URL,
            "apiBaseUrl": SERVER_URL,
            "maintenance": False,
            "regions": ["auto"] + [region["code"] for region in REGIONS],
            "features": {"auth": True, "profile": True, "inventory": True, "matchmaking": True},
            "defaultRegion": "sa",
            "bestRegion": True,
        }
    )


@app.get("/bootstrap")
@app.get("/api/bootstrap")
@app.get("/api/v1/bootstrap")
def bootstrap():
    return jsonify(
        {
            "ok": True,
            "serverTime": now(),
            "name": SERVICE_NAME,
            "gameName": SERVICE_NAME,
            "version": SERVICE_VERSION,
            "tournaments": TOURNAMENTS,
            "tournamentsname": TOURNAMENTS[0],
            "tournamentsname2": TOURNAMENTS[1],
            "config": {"maintenance": False, "defaultRegion": "sa", "bestRegion": True},
            "regions": [{"id": "auto", "name": "Best Region", "online": True}] + REGIONS,
            "endpoints": {
                "login": "/auth/login",
                "profile": "/profile",
                "inventory": "/inventory",
                "matchmaking": "/matchmaking/join",
            },
        }
    )


@app.get("/tournaments")
@app.get("/api/tournaments")
@app.get("/api/v1/tournaments")
def tournaments():
    return jsonify({
        "ok": True,
        "tournaments": [
            {"id": "lend_bd_1v1", "name": TOURNAMENTS[0], "mode": "1v1", "enabled": True},
            {"id": "lend_ld_1v1", "name": TOURNAMENTS[1], "mode": "1v1", "enabled": True},
        ],
    })


@app.post("/auth/register")
@app.post("/api/auth/register")
@app.post("/api/v1/auth/register")
def register():
    data = payload()
    username = str(data.get("username") or data.get("name") or "").strip()[:32]
    if not username:
        username = f".gg/sglend{secrets.randbelow(900000) + 100000}"

    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "username": username,
        "password": str(data.get("password") or ""),
        "trophies": 0,
        "crowns": 0,
        "coins": 5000,
        "gems": 10000,
        "createdAt": now(),
    }
    USERS[user_id] = user
    token = secrets.token_urlsafe(32)
    TOKENS[token] = user_id
    return jsonify(login_response(user, token)), 201


@app.post("/auth/login")
@app.post("/api/auth/login")
@app.post("/api/v1/auth/login")
@app.post("/login")
@app.post("/api/login")
@app.post("/api/v1/login")
def login():
    data = payload()
    username = str(data.get("username") or data.get("email") or data.get("name") or "").strip()
    user = next((u for u in USERS.values() if u["username"] == username), None)
    if user is None:
        # For lobby testing, create the player automatically on first access.
        user_id = str(uuid.uuid4())
        user = {
            "id": user_id,
            "username": username or f".gg/sglend{secrets.randbelow(900000) + 100000}",
            "password": str(data.get("password") or ""),
            "trophies": 0,
            "crowns": 0,
            "coins": 5000,
            "gems": 10000,
            "createdAt": now(),
        }
        USERS[user_id] = user
    token = secrets.token_urlsafe(32)
    TOKENS[token] = user["id"]
    return jsonify(login_response(user, token))


@app.get("/profile")
@app.get("/api/profile")
@app.get("/api/v1/profile")
@app.get("/me")
@app.get("/api/me")
@app.get("/api/v1/me")
@auth_required
def profile(user):
    return jsonify({"ok": True, "user": public_user(user), "player": public_user(user), "profile": public_user(user)})


@app.get("/inventory")
@app.get("/api/inventory")
@app.get("/api/v1/inventory")
@auth_required
def inventory(user):
    return jsonify(
        {
            "ok": True,
            "userId": user["id"],
            "items": [],
            "skins": [],
            "emotes": [],
            "selectedSkin": None,
        }
    )


@app.get("/regions")
@app.get("/api/regions")
@app.get("/api/v1/regions")
def regions():
    return jsonify({"ok": True, "defaultRegion": "sa", "bestRegion": True, "regions": [{"id": "auto", "code": "auto", "name": "Best Region", "online": True, "players": 0}] + [{**region, "id": region["code"], "online": True, "players": 0} for region in REGIONS]})


@app.post("/matchmaking/join")
@app.post("/api/matchmaking/join")
@app.post("/api/v1/matchmaking/join")
@app.post("/matchmaking")
@auth_required
def matchmaking_join(user):
    data = payload()
    match_id = str(uuid.uuid4())
    MATCHES[match_id] = {
        "id": match_id,
        "matchId": match_id,
        "status": "waiting",
        "mode": data.get("mode", "classic"),
        "region": data.get("region", "auto"),
        "players": [{"id": user["id"], "username": user["username"]}],
        "createdAt": now(),
    }
    return jsonify({"ok": True, "success": True, "match": MATCHES[match_id], "room": MATCHES[match_id]})


@app.get("/matchmaking/status/<match_id>")
@app.get("/api/matchmaking/status/<match_id>")
@app.get("/api/v1/matchmaking/status/<match_id>")
@auth_required
def matchmaking_status(user, match_id):
    match = MATCHES.get(match_id)
    if not match:
        return json_error("match not found", 404, "not_found")
    return jsonify({"ok": True, "match": match, "status": match["status"]})


@app.get("/playername")
@app.get("/api/playername")
@app.get("/api/v1/playername")
def playername():
    number = secrets.randbelow(900000) + 100000
    name = f".gg/sglend{number}"
    return jsonify({"ok": True, "playername": name, "playerName": name, "serverNumber": str(number)})


@app.post("/logout")
@app.post("/api/logout")
@app.post("/api/v1/logout")
def logout():
    token = get_token()
    if token:
        TOKENS.pop(token, None)
    return jsonify({"ok": True, "success": True})


@app.errorhandler(404)
def not_found(_error):
    return json_error("not_found", 404, "not_found")


@app.errorhandler(405)
def method_not_allowed(_error):
    return json_error("method_not_allowed", 405, "method_not_allowed")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, debug=False)
















    




