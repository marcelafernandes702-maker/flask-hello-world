import os
import time
import uuid
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configuração compatível com o APK StumbleGuys 0.33 analisado
GAME_VERSION = "0.33"
PHOTON_APP_VERSION = "0.3"
PHOTON_REGION = "eu"
PHOTON_APP_ID = "06ff7df2-1af3-4f4c-91b8-f1a6c5ed61b1"
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


@app.post("/")
def root_post_compatibility():
    """Fallback temporário para clientes que enviam /?v=:5010/user/login."""
    hint = request.args.get("v", "")
    if "/user/login" in hint:
        return backbone_user_login()
    if "/user/connect" in hint:
        return backbone_user_connect()
    if "/user/refreshAccessToken" in hint:
        return backbone_refresh_token()
    return jsonify({
        "success": False,
        "error": "unsupported_root_post",
        "path": request.path,
        "hint": hint,
    }), 404


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


def _backbone_identity():
    """Cria uma identidade de teste estável para o fluxo local do APK."""
    data = request.get_json(silent=True) or {}
    device_id = (
        data.get("deviceId")
        or data.get("device_id")
        or request.headers.get("X-Device-Id")
        or "local-device"
    )
    user_id = f"guest-{str(device_id)[:48]}"
    access_token = f"trice-access-{uuid.uuid5(uuid.NAMESPACE_URL, str(device_id)).hex}"
    refresh_token = f"trice-refresh-{uuid.uuid5(uuid.NAMESPACE_DNS, str(device_id)).hex}"
    return data, device_id, user_id, access_token, refresh_token


@app.post("/api/v1/userLogin")
@app.post("/user/login")
def backbone_user_login():
    """Compatibilidade inicial com o login Backbone usado pelo APK 0.33."""
    _data, device_id, user_id, access_token, refresh_token = _backbone_identity()
    return jsonify({
        "success": True,
        "authenticated": True,
        "userId": user_id,
        "user_id": user_id,
        "deviceId": device_id,
        "accessToken": access_token,
        "access_token": access_token,
        "refreshToken": refresh_token,
        "refresh_token": refresh_token,
        "token": access_token,
        "displayName": DISPLAY_NAME,
        "display_name": DISPLAY_NAME,
        "gameVersion": GAME_VERSION,
        "game_version": GAME_VERSION,
    }), 200


@app.post("/api/v1/userConnect")
@app.post("/user/connect")
def backbone_user_connect():
    """Aceita a conexão após o login e devolve os mesmos tokens."""
    _data, device_id, user_id, access_token, refresh_token = _backbone_identity()
    return jsonify({
        "success": True,
        "authenticated": True,
        "connected": True,
        "userId": user_id,
        "user_id": user_id,
        "deviceId": device_id,
        "accessToken": access_token,
        "access_token": access_token,
        "refreshToken": refresh_token,
        "refresh_token": refresh_token,
        "token": access_token,
    }), 200


@app.post("/api/v1/refreshAccessToken")
@app.post("/user/refreshAccessToken")
def backbone_refresh_token():
    """Compatibilidade com a renovação de sessão do cliente Backbone."""
    _data, device_id, user_id, access_token, refresh_token = _backbone_identity()
    return jsonify({
        "success": True,
        "authenticated": True,
        "userId": user_id,
        "deviceId": device_id,
        "accessToken": access_token,
        "access_token": access_token,
        "refreshToken": refresh_token,
        "refresh_token": refresh_token,
        "token": access_token,
    }), 200


@app.route("/api/v1/ping", methods=["GET", "POST"])
@app.route("/user/ping", methods=["GET", "POST"])
def backbone_ping():
    return jsonify({"success": True, "ok": True, "status": "online"}), 200


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










    




