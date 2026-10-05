import os
import time
import uuid
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configuração compatível com o APK StumbleGuys 0.33 analisado
GAME_VERSION = "0.33"
PHOTON_APP_VERSION = "Playtest Group Alpha"
PHOTON_REGION = "eu"
PHOTON_APP_ID = "e7c4e3ac-6a25-4ce3-8240-0c25501b4c76"
BASE_URL = "https://trice-stumbled-backend.onrender.com/api"
SERVER_NAME = "Trice-Stumbled"
DISPLAY_NAME = "TriceStumbled<color=orange><sup>#151"


def config_payload():
    """Formato centralizado para evitar respostas diferentes entre as rotas."""
    return {
        "server": SERVER_NAME,
        "server_name": SERVER_NAME,
        "game_version": GAME_VERSION,
        "version": GAME_VERSION,
        "app_version": PHOTON_APP_VERSION,
        "photon_app_version": PHOTON_APP_VERSION,
        "photon_app_id": PHOTON_APP_ID,
        "photon_required": True,
        "region": PHOTON_REGION,
        "photon_region": PHOTON_REGION,
        "backend_url": BASE_URL,
        "server_url": BASE_URL,
        "matchmaking_enabled": True,
        "maintenance": False,
    }


@app.get("/")
def root():
    # Compatibilidade: alguns clientes consultam a raiz em vez de /api/config.
    payload = config_payload()
    payload["root_compatibility"] = True
    return jsonify(payload), 200


@app.get("/api")
@app.get("/api/")
def api_root():
    return jsonify({
        "ok": True,
        "status": "online",
        "server": SERVER_NAME,
        "version": GAME_VERSION,
        "config_url": f"{BASE_URL}/config",
    }), 200


@app.get("/api/health")
@app.get("/api/healthz")
def health():
    return jsonify({
        "ok": True,
        "status": "online",
        "server": SERVER_NAME,
        "version": GAME_VERSION,
    }), 200


@app.get("/api/status")
def status():
    return jsonify({
        "active_rooms": 0,
        "game_version": GAME_VERSION,
        "maintenance": False,
        "matchmaking_enabled": True,
        "online": True,
        "online_players": 0,
        "region": PHOTON_REGION,
        "server": SERVER_NAME,
        "server_name": SERVER_NAME,
        "status": "online",
        "time": int(time.time()),
        "version": GAME_VERSION,
    }), 200


@app.get("/api/config")
def config():
    # O APK acrescenta ?v=0.33&x=...; os parâmetros são aceitos e ignorados.
    return jsonify(config_payload()), 200


@app.get("/api/profile")
def profile():
    return jsonify({
        "player_id": request.headers.get("X-Player-Id", "local-player"),
        "display_name": DISPLAY_NAME,
        "displayName": DISPLAY_NAME,
        "coins": 5000,
        "gems": 19650,
        "skin": "default",
    }), 200


@app.post("/api/auth/guest")
def guest_login():
    player_id = request.headers.get("X-Player-Id") or f"guest-{uuid.uuid4().hex[:12]}"
    return jsonify({
        "success": True,
        "authenticated": True,
        "token": player_id,
        "session_token": player_id,
        "player_id": player_id,
        "display_name": DISPLAY_NAME,
        "displayName": DISPLAY_NAME,
        "game_version": GAME_VERSION,
    }), 200


@app.errorhandler(404)
def not_found(_error):
    return jsonify({
        "success": False,
        "error": "route_not_found",
        "path": request.path,
    }), 404


@app.errorhandler(400)
def bad_request(_error):
    return jsonify({
        "success": False,
        "error": "bad_request",
    }), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)





    




