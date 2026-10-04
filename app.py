import os
import time
import uuid
from threading import Lock
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

PORT = int(os.environ.get("PORT", "10000"))
VERSION = "0.33"
SERVER_NAME = "Trice-Stumbled"
BASE_URL = os.environ.get("PUBLIC_BASE_URL", "https://stumble-rewald.onrender.com").rstrip("/")

_lock = Lock()
players = {}
rooms = {}


def json_body():
    return request.get_json(silent=True) or {}


def player_from_body(data):
    player_id = str(data.get("player_id") or data.get("id") or "local-player")
    name = str(data.get("display_name") or data.get("name") or ".gg/sgrewald")[:24]
    return player_id, name


def room_snapshot(room):
    return {
        "room_id": room["room_id"],
        "state": room["state"],
        "players": len(room["players"]),
        "max_players": room["max_players"],
        "version": VERSION,
        "region": room["region"],
        "created_at": room["created_at"],
    }


@app.get("/")
def index():
    return "Trice-Stumbled 0.33 ONLINE", 200


@app.get("/health")
@app.get("/api/health")
def health():
    return jsonify({"ok": True, "status": "online", "server": SERVER_NAME, "version": VERSION}), 200


@app.get("/api/status")
@app.get("/api/v1/status")
def status():
    with _lock:
        active_rooms = len(rooms)
        online_players = len(players)
    return jsonify({
        "online": True,
        "status": "online",
        "server": SERVER_NAME,
        "server_name": SERVER_NAME,
        "game_version": VERSION,
        "version": VERSION,
        "region": "sa",
        "maintenance": False,
        "matchmaking_enabled": True,
        "active_rooms": active_rooms,
        "online_players": online_players,
        "time": int(time.time()),
    }), 200


@app.get("/api/config")
@app.get("/api/v1/config")
def config():
    return jsonify({
        "server": SERVER_NAME,
        "game_version": VERSION,
        "region": "sa",
        "matchmaking_enabled": True,
        "photon_required": True,
        "backend_url": BASE_URL,
        "server_url": BASE_URL,
        "message_connecting": "Conectando nos servidores do Trice-Stumbled",
        "message_searching": "Procurando salas do Trice-Stumbled",
        "message_waiting": "À espera de jogadores",
    }), 200


@app.get("/api/profile")
@app.get("/api/v1/profile")
def profile():
    player_id = request.args.get("player_id", "local-player")
    with _lock:
        p = players.get(player_id, {
            "player_id": player_id,
            "display_name": ".gg/sgrewald",
            "coins": 5000,
            "gems": 19650,
            "skin": "default",
        })
    return jsonify(p), 200


@app.post("/api/login")
@app.post("/api/v1/login")
def login():
    data = json_body()
    player_id, name = player_from_body(data)
    with _lock:
        players.setdefault(player_id, {
            "player_id": player_id,
            "display_name": name,
            "coins": 5000,
            "gems": 19650,
            "skin": "default",
        })
        players[player_id]["online"] = True
    return jsonify({
        "success": True,
        "ok": True,
        "token": f"local-{player_id}",
        "player_id": player_id,
        "display_name": name,
        "version": VERSION,
    }), 200


@app.post("/api/profile/update")
def profile_update():
    data = json_body()
    player_id, name = player_from_body(data)
    with _lock:
        p = players.setdefault(player_id, {"player_id": player_id})
        p["display_name"] = name
        if "skin" in data:
            p["skin"] = str(data["skin"])[:80]
    return jsonify({"success": True, "profile": p}), 200


@app.post("/api/matchmaking/start")
@app.post("/api/v1/matchmaking/start")
def matchmaking_start():
    data = json_body()
    player_id, name = player_from_body(data)
    with _lock:
        players.setdefault(player_id, {"player_id": player_id, "display_name": name})
        room = next((r for r in rooms.values() if r["state"] == "waiting" and len(r["players"]) < r["max_players"]), None)
        if room is None:
            room_id = f"rewald-{uuid.uuid4().hex[:8]}"
            room = {"room_id": room_id, "state": "waiting", "players": {}, "max_players": 32, "region": "sa", "created_at": int(time.time())}
            rooms[room_id] = room
        room["players"][player_id] = {"player_id": player_id, "display_name": name}
    return jsonify({"success": True, "ok": True, "state": "searching", "message": "Procurando salas do Trice-Stumbled", **room_snapshot(room)}), 200


@app.get("/api/matchmaking/status")
@app.get("/api/v1/matchmaking/status")
def matchmaking_status():
    room_id = request.args.get("room_id")
    with _lock:
        room = rooms.get(room_id) if room_id else next(iter(rooms.values()), None)
        if room is None:
            return jsonify({"success": True, "state": "idle", "message": "Nenhuma sala encontrada", "players": 0}), 200
        return jsonify({"success": True, "message": "À espera de jogadores", **room_snapshot(room)}), 200


@app.post("/api/matchmaking/stop")
@app.post("/api/v1/matchmaking/stop")
def matchmaking_stop():
    data = json_body()
    room_id = data.get("room_id")
    with _lock:
        if room_id in rooms:
            rooms[room_id]["state"] = "closed"
    return jsonify({"success": True, "state": "stopped", "room_id": room_id}), 200


@app.get("/api/rooms")
def list_rooms():
    with _lock:
        result = [room_snapshot(r) for r in rooms.values() if r["state"] == "waiting"]
    return jsonify({"success": True, "rooms": result}), 200


@app.errorhandler(404)
def not_found(_):
    return jsonify({"success": False, "error": "route_not_found", "path": request.path}), 404


@app.errorhandler(500)
def server_error(_):
    return jsonify({"success": False, "error": "internal_server_error"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)



    




