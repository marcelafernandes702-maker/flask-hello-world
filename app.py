import os
import secrets
from datetime import datetime, timedelta, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

VERSION = os.environ.get("GAME_VERSION", "0.33.0")
players = {}
sessions = {}


def json_data():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def get_player():
    data = json_data()

    player_id = (
        data.get("playerId")
        or data.get("userId")
        or request.headers.get("X-Player-Id")
        or "guest-player"
    )

    name = (
        data.get("displayName")
        or data.get("nickname")
        or "zPedroxDev"
    )

    player_id = str(player_id)

    if player_id not in players:
        players[player_id] = {
            "playerId": player_id,
            "displayName": str(name)[:24],
            "level": 1,
            "xp": 0,
            "coins": 9999,
            "gems": 100,
            "isBanned": False
        }

    players[player_id]["displayName"] = str(name)[:24]
    return players[player_id]


def profile(player):
    return {
        "playerId": player["playerId"],
        "id": player["playerId"],
        "displayName": player["displayName"],
        "nickname": player["displayName"],
        "name": player["displayName"],
        "level": player["level"],
        "xp": player["xp"],
        "coins": player["coins"],
        "gems": player["gems"],
        "isBanned": False,
        "onboardingComplete": True
    }


def inventory(player):
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


@app.get("/")
def home():
    return jsonify({
        "ok": True,
        "service": "Rewald API",
        "status": "online",
        "version": VERSION
    })


@app.route("/api", methods=["GET", "POST", "OPTIONS"])
@app.route("/api/", methods=["GET", "POST", "OPTIONS"])
def api_root():
    return jsonify({
        "ok": True,
        "status": "online",
        "version": VERSION,
        "maintenance": False
    })


@app.route("/api/status", methods=["GET", "POST", "OPTIONS"])
def status():
    return jsonify({
        "ok": True,
        "success": True,
        "status": "online",
        "version": VERSION,
        "maintenance": False
    })


@app.route("/api/health", methods=["GET", "POST", "OPTIONS"])
def health():
    return jsonify({
        "ok": True,
        "status": "healthy",
        "version": VERSION
    })


@app.route("/api/auth/login", methods=["GET", "POST", "OPTIONS"])
def login():
    player = get_player()
    token = secrets.token_urlsafe(32)

    expires = datetime.now(timezone.utc) + timedelta(days=1)

    sessions[token] = {
        "playerId": player["playerId"],
        "expiresAt": expires.isoformat()
    }

    return jsonify({
        "ok": True,
        "success": True,
        "code": 0,
        "token": token,
        "sessionToken": token,
        "session": {
            "sessionId": token,
            "playerId": player["playerId"],
            "expiresAt": expires.isoformat(),
            "protocolVersion": VERSION
        },
        "profile": profile(player),
        "inventory": inventory(player)
    })


@app.route("/api/session", methods=["GET", "POST", "OPTIONS"])
def session():
    player = get_player()

    return jsonify({
        "ok": True,
        "success": True,
        "session": {
            "sessionId": "guest-session",
            "playerId": player["playerId"],
            "protocolVersion": VERSION
        },
        "profile": profile(player)
    })


@app.route("/api/profile", methods=["GET", "POST", "OPTIONS"])
def profile_route():
    player = get_player()
    return jsonify({
        "ok": True,
        "success": True,
        "profile": profile(player),
        **profile(player)
    })


@app.route("/api/user", methods=["GET", "POST", "OPTIONS"])
def user():
    player = get_player()

    return jsonify({
        "ok": True,
        "success": True,
        "id": player["playerId"],
        "name": player["displayName"],
        "nickname": player["displayName"]
    })


@app.route("/api/inventory", methods=["GET", "POST", "OPTIONS"])
def inventory_route():
    player = get_player()

    return jsonify({
        "ok": True,
        "success": True,
        "inventory": inventory(player),
        **inventory(player)
    })


@app.route("/api/lobby/join", methods=["GET", "POST", "OPTIONS"])
def lobby_join():
    player = get_player()

    return jsonify({
        "ok": True,
        "success": True,
        "joined": True,
        "code": 0,
        "lobby": {
            "id": "rewald-lobby",
            "state": "waiting",
            "players": [profile(player)]
        }
    })


@app.route("/api/compatibility", methods=["GET", "POST", "OPTIONS"])
def compatibility():
    return jsonify({
        "ok": True,
        "compatible": True,
        "version": VERSION,
        "maintenance": False
    })


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "ok": False,
        "error": "not_found"
    }), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)



