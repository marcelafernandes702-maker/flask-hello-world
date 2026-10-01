import os
import secrets
from datetime import datetime, timezone, timedelta

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

VERSION = "0.33.0"
TOKEN_EXPIRATION = 86400


def input_data():
    data = request.get_json(silent=True)

    if isinstance(data, dict):
        return data

    return {}


def make_player():
    data = input_data()

    player_id = (
        data.get("playerId")
        or data.get("userId")
        or data.get("id")
        or request.headers.get("X-Player-Id")
        or "player-0"
    )

    player_name = (
        data.get("displayName")
        or data.get("nickname")
        or data.get("name")
        or "zPedroxDev"
    )

    return {
        "id": str(player_id),
        "playerId": str(player_id),
        "userId": str(player_id),
        "name": str(player_name)[:24],
        "nickname": str(player_name)[:24],
        "displayName": str(player_name)[:24],
        "level": 1,
        "xp": 0,
        "trophies": 0,
        "crowns": 0,
        "coins": 9999,
        "gems": 100,
        "isBanned": False,
        "onboardingComplete": True
    }


def make_inventory(player):
    return {
        "items": [
            {
                "id": "starter-kit",
                "type": "starter",
                "quantity": 1
            }
        ],
        "currencies": {
            "coins": player["coins"],
            "gems": player["gems"]
        }
    }


def make_session(player):
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(seconds=TOKEN_EXPIRATION)

    return {
        "sessionId": token,
        "sessionToken": token,
        "token": token,
        "playerId": player["playerId"],
        "expiresAt": expires.isoformat(),
        "protocolVersion": VERSION
    }


def standard_response(player=None):
    player = player or make_player()

    return {
        "ok": True,
        "success": True,
        "code": 0,
        "status": "online",
        "version": VERSION,
        "maintenance": False,
        "profile": player,
        "user": player,
        "player": player,
        "inventory": make_inventory(player)
    }


@app.route("/", methods=["GET", "POST", "OPTIONS"])
def home():
    return jsonify({
        "ok": True,
        "success": True,
        "service": "Rewald API",
        "status": "online",
        "version": VERSION
    })


@app.route("/api", methods=["GET", "POST", "OPTIONS"])
@app.route("/api/", methods=["GET", "POST", "OPTIONS"])
def api_root():
    return jsonify(standard_response())


@app.route("/api/status", methods=["GET", "POST", "OPTIONS"])
@app.route("/api/status/", methods=["GET", "POST", "OPTIONS"])
def api_status():
    return jsonify({
        "ok": True,
        "success": True,
        "code": 0,
        "status": "online",
        "version": VERSION,
        "maintenance": False,
        "server": "rewald",
        "ready": True
    })


@app.route("/api/health", methods=["GET", "POST", "OPTIONS"])
@app.route("/health", methods=["GET", "POST", "OPTIONS"])
def health():
    return jsonify({
        "ok": True,
        "success": True,
        "status": "healthy",
        "version": VERSION
    })


@app.route("/api/auth/login", methods=["GET", "POST", "OPTIONS"])
@app.route("/api/login", methods=["GET", "POST", "OPTIONS"])
def login():
    player = make_player()
    session = make_session(player)

    return jsonify({
        "ok": True,
        "success": True,
        "code": 0,
        "status": "online",
        "authenticated": True,
        "loggedIn": True,
        "token": session["token"],
        "sessionToken": session["sessionToken"],
        "session": session,
        "profile": player,
        "user": player,
        "player": player,
        "inventory": make_inventory(player)
    })


@app.route("/api/session", methods=["GET", "POST", "OPTIONS"])
@app.route("/api/auth/session", methods=["GET", "POST", "OPTIONS"])
def session():
    player = make_player()
    session_data = make_session(player)

    return jsonify({
        "ok": True,
        "success": True,
        "authenticated": True,
        "session": session_data,
        "profile": player,
        "user": player
    })


@app.route("/api/profile", methods=["GET", "POST", "OPTIONS"])
@app.route("/api/user/profile", methods=["GET", "POST", "OPTIONS"])
def profile():
    player = make_player()

    return jsonify({
        "ok": True,
        "success": True,
        "profile": player,
        "user": player,
        "player": player,
        **player
    })


@app.route("/api/user", methods=["GET", "POST", "OPTIONS"])
def user():
    player = make_player()

    return jsonify({
        "ok": True,
        "success": True,
        "user": player,
        "profile": player,
        "player": player
    })


@app.route("/api/inventory", methods=["GET", "POST", "OPTIONS"])
@app.route("/api/user/inventory", methods=["GET", "POST", "OPTIONS"])
def inventory():
    player = make_player()
    items = make_inventory(player)

    return jsonify({
        "ok": True,
        "success": True,
        "inventory": items,
        "items": items["items"],
        "currencies": items["currencies"]
    })


@app.route("/api/lobby/join", methods=["GET", "POST", "OPTIONS"])
@app.route("/api/lobby", methods=["GET", "POST", "OPTIONS"])
@app.route("/api/matchmaking/join", methods=["GET", "POST", "OPTIONS"])
def join_lobby():
    player = make_player()

    return jsonify({
        "ok": True,
        "success": True,
        "code": 0,
        "joined": True,
        "connected": True,
        "inLobby": True,
        "lobbyId": "rewald-lobby",
        "matchId": "rewald-lobby",
        "lobby": {
            "id": "rewald-lobby",
            "lobbyId": "rewald-lobby",
            "state": "waiting",
            "status": "open",
            "players": [player],
            "maxPlayers": 32
        },
        "player": player
    })


@app.route("/api/compatibility", methods=["GET", "POST", "OPTIONS"])
@app.route("/api/version", methods=["GET", "POST", "OPTIONS"])
def compatibility():
    return jsonify({
        "ok": True,
        "success": True,
        "compatible": True,
        "supported": True,
        "version": VERSION,
        "protocolVersion": VERSION,
        "maintenance": False
    })


@app.route("/api/<path:unknown_path>", methods=[
    "GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"
])
def unknown_api_route(unknown_path):
    """
    Resposta de compatibilidade para endpoints adicionais
    que a versão antiga possa chamar.
    """
    player = make_player()

    return jsonify({
        "ok": True,
        "success": True,
        "code": 0,
        "status": "online",
        "ready": True,
        "path": "/api/" + unknown_path,
        "version": VERSION,
        "maintenance": False,
        "authenticated": True,
        "profile": player,
        "user": player,
        "player": player,
        "inventory": make_inventory(player),
        "session": make_session(player),
        "lobby": {
            "id": "rewald-lobby",
            "state": "waiting",
            "players": [player]
        }
    })


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "ok": False,
        "success": False,
        "error": "not_found"
    }), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({
        "ok": False,
        "success": False,
        "error": "server_error"
    }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)

    




