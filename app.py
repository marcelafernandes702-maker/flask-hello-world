import os

from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "ok": True,
        "service": "Rewald API",
        "status": "online",
        "version": "0.33.0"
    }), 200


@app.route("/api", methods=["GET", "POST", "OPTIONS"])
@app.route("/api/", methods=["GET", "POST", "OPTIONS"])
def api_root():
    return jsonify({
        "ok": True,
        "success": True,
        "status": "online",
        "version": "0.33.0",
        "maintenance": False
    }), 200


@app.route("/api/status", methods=["GET", "POST", "OPTIONS"])
def api_status():
    return jsonify({
        "ok": True,
        "success": True,
        "status": "online",
        "version": "0.33.0",
        "maintenance": False
    }), 200


@app.route("/api/health", methods=["GET", "POST", "OPTIONS"])
def api_health():
    return jsonify({
        "ok": True,
        "success": True,
        "status": "healthy",
        "version": "0.33.0"
    }), 200


@app.route("/api/compatibility", methods=["GET", "POST", "OPTIONS"])
def compatibility():
    return jsonify({
        "ok": True,
        "compatible": True,
        "version": "0.33.0",
        "maintenance": False
    }), 200


@app.errorhandler(404)
def route_not_found(error):
    return jsonify({
        "ok": False,
        "success": False,
        "error": "not_found",
        "message": "Rota não encontrada"
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "ok": False,
        "success": False,
        "error": "method_not_allowed"
    }), 405


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)




