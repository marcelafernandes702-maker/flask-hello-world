import os
import secrets
from datetime import datetime, timezone
from flask import Flask, jsonify, request

app = Flask(__name__)

SUPPORTED_VERSIONS = [f"0.{minor}" for minor in range(50, 71)]
MIN_VERSION = "0.50"
MAX_VERSION = "0.70"
LATEST_VERSION = "0.70"

SERVER_INFO = {
    "service": "game-backend",
    "status": "online",
    "botName": "PlayerzPedrox",
    "tournamentsName": "zPedrox Dev Tbest",
}


def version_from_request():
    payload = request.get_json(silent=True) or {}
    return (
        payload.get("version")
        or request.args.get("version")
        or request.headers.get("X-Game-Version")
        or "0.56"
    )


def transfer_popup(version):
    return {
        "enabled": True,
        "showOnFirstLaunch": True,
        "title": "Transfer elements",
        "message": "Transferring required updates to enter the lobby...",
        "requiredUpdate": True,
        "version": version,
        "progressEnabled": True,
        "canSkip": False,
    }


def base_response(version):
    return {
        "success": True,
        "server": SERVER_INFO,
        "gameVersion": version,
        "supportedVersions": SUPPORTED_VERSIONS,
        "loadingPopup": transfer_popup(version),
    }


@app.after_request
def add_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Game-Version"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/api/user/login", methods=["GET", "POST", "OPTIONS"])
def user_login():
    if request.method == "OPTIONS":
        return ("", 204)
    payload = request.get_json(silent=True) or {}
    version = version_from_request()
    username = payload.get("username") or payload.get("userName") or "Guest"
    response = base_response(version)
    response.update({
        "authenticated": True,
        "token": secrets.token_urlsafe(24),
        "user": {"id": username, "username": username},
        "firstLaunch": True,
    })
    return jsonify(response)


@app.route("/api/info", methods=["GET", "OPTIONS"])
def api_info():
    if request.method == "OPTIONS":
        return ("", 204)
    version = version_from_request()
    return jsonify({
        "success": True,
        "name": "Lobby",
        "gameVersion": version,
        "minVersion": MIN_VERSION,
        "maxVersion": MAX_VERSION,
        "botName": SERVER_INFO["botName"],
        "tournamentsName": SERVER_INFO["tournamentsName"],
        "loadingPopup": transfer_popup(version),
    })


@app.route("/api/config", methods=["GET", "OPTIONS"])
def api_config():
    if request.method == "OPTIONS":
        return ("", 204)
    version = version_from_request()
    return jsonify({
        "success": True,
        "maintenance": False,
        "loginEnabled": True,
        "registrationEnabled": True,
        "contentUpdateRequired": True,
        "loadingPopup": transfer_popup(version),
        "supportedVersions": SUPPORTED_VERSIONS,
    })


@app.route("/api/version", methods=["GET", "OPTIONS"])
def api_version():
    if request.method == "OPTIONS":
        return ("", 204)
    version = version_from_request()
    return jsonify({
        "success": True,
        "version": version,
        "minVersion": MIN_VERSION,
        "maxVersion": MAX_VERSION,
        "latestVersion": LATEST_VERSION,
        "updateRequired": False,
        "contentUpdateRequired": True,
        "loadingPopup": transfer_popup(version),
    })


@app.route("/api/status", methods=["GET", "OPTIONS"])
def api_status():
    if request.method == "OPTIONS":
        return ("", 204)
    return jsonify({
        "success": True,
        "status": "online",
        "online": True,
        "api": "online",
        "service": SERVER_INFO["service"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.get("/api/game-info")
def game_info():
    return jsonify({
        "success": True,
        "versions": {"min": MIN_VERSION, "max": MAX_VERSION},
        "botName": SERVER_INFO["botName"],
        "tournamentsName": SERVER_INFO["tournamentsName"],
    })


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": SERVER_INFO["service"]})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)














    




