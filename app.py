"""REST backend for the Stumble Lend lobby."""

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

SERVICE_NAME = "Stumble Lend"
SERVICE_VERSION = "0.50"
SERVER_URL = os.environ.get("PUBLIC_BASE_URL", "https://sglend-backend.onrender.com")
TOURNAMENTS = ["Lend BD 1v1", "Lend LD 1v1"]
REGIONS = ["auto", "asia", "au", "cae", "cn", "eu", "hk", "in", "jp", "za", "sa", "kr", "tr", "uae", "us", "usw", "ussc"]

USERS: Dict[str, Dict[str, Any]] = {}
TOKENS: Dict[str, str] = {}
MATCHES: Dict[str, Dict[str, Any]] = {}


def now() -> int:
    return int(time.time())


def body() -> Dict[str, Any]:
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else request.form.to_dict()


def error(message: str, status: int = 400, code: str = "bad_request"):
    return jsonify({"ok": False, "error": code, "message": message}), status


def token_from_request() -> Optional[str]:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return request.headers.get("X-Auth-Token") or request.args.get("token")


def get_user() -> Optional[Dict[str, Any]]:
    token = token_from_request()
    return USERS.get(TOKENS.get(token or "", ""))


def requires_auth(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        user = get_user()
        if user is None:
            return error("authentication required", 401, "unauthorized")
        return fn(user, *args, **kwargs)

    return wrapped


def player_data(user: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": user["id"],
        "userId": user["id"],
        "username": user["username"],
        "displayName": user["username"],
        "playerName": user["username"],
        "playername": user["username"],
        "serverNumber": user["username"].replace(".gg/sglend", ""),
        "name": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "trophies": user["trophies"],
        "crowns": user["crowns"],
        "coins": user["coins"],
        "gems": user["gems"],
        "createdAt": user["createdAt"],
        "tournamentsname": TOURNAMENTS[0],
        "tournamentsname2": TOURNAMENTS[1],
    }


def new_player(username: str = "") -> Dict[str, Any]:
    if not username:
        username = f".gg/sglend{secrets.randbelow(900000) + 100000}"
    user = {
        "id": str(uuid.uuid4()),
        "username": username[:32],
        "trophies": 0,
        "crowns": 0,
        "coins": 5000,
        "gems": 10000,
        "createdAt": now(),
    }
    USERS[user["id"]] = user
    return user


@app.after_request
def cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Auth-Token"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.get("/")
def index():
    return jsonify({"ok": True, "service": SERVICE_NAME, "game": SERVICE_NAME, "version": SERVICE_VERSION, "status": "online", "health": f"{SERVER_URL}/health", "tournaments": TOURNAMENTS, "tournamentsname": TOURNAMENTS[0], "tournamentsname2": TOURNAMENTS[1]})


@app.get("/health")
@app.get("/healthz")
@app.get("/api/health")
def health():
    return jsonify({"ok": True, "status": "ok", "service": "sglend-backend", "timestamp": now()})


@app.get("/status")
@app.get("/api/status")
@app.get("/api/v1/status")
def status():
    return jsonify({"ok": True, "status": "online", "service": SERVICE_NAME, "version": SERVICE_VERSION, "backend": SERVER_URL, "timestamp": now()})


@app.get("/version")
@app.get("/api/version")
def version():
    return jsonify({"ok": True, "version": SERVICE_VERSION})


@app.get("/config")
@app.get("/api/config")
@app.get("/api/v1/config")
def config():
    return jsonify({"ok": True, "name": SERVICE_NAME, "gameName": SERVICE_NAME, "version": SERVICE_VERSION, "server": SERVER_URL, "apiBaseUrl": SERVER_URL, "maintenance": False, "defaultRegion": "sa", "bestRegion": True, "regions": REGIONS, "features": {"auth": True, "profile": True, "inventory": True, "matchmaking": True}, "tournaments": TOURNAMENTS, "tournamentsname": TOURNAMENTS[0], "tournamentsname2": TOURNAMENTS[1]})


@app.get("/bootstrap")
@app.get("/api/bootstrap")
@app.get("/api/v1/bootstrap")
def bootstrap():
    return jsonify({"ok": True, "name": SERVICE_NAME, "gameName": SERVICE_NAME, "version": SERVICE_VERSION, "serverTime": now(), "config": {"maintenance": False, "defaultRegion": "sa", "bestRegion": True}, "endpoints": {"login": "/auth/login", "profile": "/profile", "inventory": "/inventory", "matchmaking": "/matchmaking/join"}, "regions": REGIONS, "tournaments": TOURNAMENTS, "tournamentsname": TOURNAMENTS[0], "tournamentsname2": TOURNAMENTS[1]})


@app.post("/auth/login")
@app.post("/api/auth/login")
@app.post("/api/v1/auth/login")
@app.post("/login")
@app.post("/api/login")
@app.post("/api/v1/login")
def login():
    data = body()
    username = str(data.get("username") or data.get("name") or data.get("email") or "").strip()
    user = next((item for item in USERS.values() if item["username"] == username), None) or new_player(username)
    access_token = secrets.token_urlsafe(32)
    TOKENS[access_token] = user["id"]
    player = player_data(user)
    return jsonify({"ok": True, "success": True, "token": access_token, "accessToken": access_token, "sessionToken": access_token, "expiresIn": 2592000, "user": player, "player": player, "profile": player})


@app.post("/auth/register")
@app.post("/api/auth/register")
@app.post("/api/v1/auth/register")
def register():
    return login()


@app.get("/profile")
@app.get("/api/profile")
@app.get("/api/v1/profile")
@app.get("/me")
@app.get("/api/me")
@app.get("/api/v1/me")
@requires_auth
def profile(user):
    player = player_data(user)
    return jsonify({"ok": True, "user": player, "player": player, "profile": player})


@app.get("/inventory")
@app.get("/api/inventory")
@app.get("/api/v1/inventory")
@requires_auth
def inventory(user):
    return jsonify({"ok": True, "userId": user["id"], "items": [], "skins": [], "emotes": [], "selectedSkin": None})


@app.get("/regions")
@app.get("/api/regions")
@app.get("/api/v1/regions")
def regions():
    return jsonify({"ok": True, "defaultRegion": "sa", "bestRegion": True, "regions": [{"id": code, "code": code, "name": code, "online": True, "players": 0} for code in REGIONS]})


@app.get("/tournaments")
@app.get("/api/tournaments")
@app.get("/api/v1/tournaments")
def tournaments():
    return jsonify({"ok": True, "tournaments": [{"id": "lend_bd_1v1", "name": TOURNAMENTS[0], "mode": "1v1", "enabled": True}, {"id": "lend_ld_1v1", "name": TOURNAMENTS[1], "mode": "1v1", "enabled": True}]})


@app.get("/playername")
@app.get("/api/playername")
@app.get("/api/v1/playername")
def playername():
    number = secrets.randbelow(900000) + 100000
    value = f".gg/sglend{number}"
    return jsonify({"ok": True, "playerName": value, "playername": value, "serverNumber": str(number)})


@app.post("/matchmaking/join")
@app.post("/api/matchmaking/join")
@app.post("/api/v1/matchmaking/join")
@app.post("/matchmaking")
@requires_auth
def join_match(user):
    data = body()
    match_id = str(uuid.uuid4())
    match = {"id": match_id, "matchId": match_id, "status": "waiting", "mode": data.get("mode", "classic"), "region": data.get("region", "sa"), "players": [{"id": user["id"], "username": user["username"]}], "createdAt": now()}
    MATCHES[match_id] = match
    return jsonify({"ok": True, "success": True, "match": match, "room": match})


@app.get("/matchmaking/status/<match_id>")
@app.get("/api/matchmaking/status/<match_id>")
@app.get("/api/v1/matchmaking/status/<match_id>")
@requires_auth
def match_status(user, match_id):
    match = MATCHES.get(match_id)
    if not match:
        return error("match not found", 404, "not_found")
    return jsonify({"ok": True, "match": match, "status": match["status"]})


@app.post("/logout")
@app.post("/api/logout")
@app.post("/api/v1/logout")
def logout():
    token = token_from_request()
    if token:
        TOKENS.pop(token, None)
    return jsonify({"ok": True, "success": True})


@app.errorhandler(404)
def not_found(_error):
    return error("not_found", 404, "not_found")


@app.errorhandler(405)
def method_not_allowed(_error):
    return error("method_not_allowed", 405, "method_not_allowed")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")), debug=False)

















    




