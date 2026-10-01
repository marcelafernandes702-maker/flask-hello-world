from flask import Flask, jsonify

app = Flask(__name__)

# Main API endpoint — for game connection
@app.route("/api", methods=["GET", "POST"])
def api():
    return jsonify({
        "server_name": "Stumble Rewald",
        "version": "0.33",
        "discord": "https://discord.gg/sgrewald",
        "status": "online",
        "protocol": "1.0"
    })

# Status check — heartbeat
@app.route("/api/status", methods=["GET", "POST"])
def status():
    return jsonify({
        "status": "active",
        "online": True,
        "ready": True,
        "timestamp": "2026-10-01T13:25:00Z"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)


