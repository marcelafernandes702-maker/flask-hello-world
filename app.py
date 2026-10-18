from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
PHOTON_QUANTUM_APP_ID = os.getenv("PHOTON_QUANTUM_APP_ID")
GAME_VERSION = "0.30"
MAX_PLAYERS_PER_ROOM = 32

# Routes
@app.route("/")
def home():
    return jsonify({
        "name": "Stumble Guys Backend",
        "version": GAME_VERSION,
        "status": "online"
    })

@app.route("/api/status")
def status():
    return jsonify({
        "status": "ok",
        "online": True,
        "version": GAME_VERSION
    })

@app.route("/api/version")
def version():
    return jsonify({
        "game_version": GAME_VERSION,
        "photon_quantum_app_id": PHOTON_QUANTUM_APP_ID,
        "max_players": MAX_PLAYERS_PER_ROOM
    })

@app.route("/api/user/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "Player")
    
    return jsonify({
        "status": "success",
        "message": "Login successful!",
        "username": username,
        "game_version": GAME_VERSION,
        "region": "sa-east-1"
    }), 200

@app.route("/api/config")
def config():
    return jsonify({
        "app_version": GAME_VERSION,
        "photon_quantum_app_id": PHOTON_QUANTUM_APP_ID,
        "default_region": "sa-east-1",
        "max_players_per_room": MAX_PLAYERS_PER_ROOM
    })

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)












    




