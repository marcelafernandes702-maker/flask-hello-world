import os
import secrets
import uuid
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, jsonify, request

app = Flask(__name__)

SERVICE_NAME = os.getenv("SERVICE_NAME", "stumble-rewald-backend")
ENVIRONMENT = os.getenv("ENVIRONMENT", "LIVE")
API_TOKEN = os.getenv("API_TOKEN", "change-this-in-render")

players = {}
rooms = {}

# Banner configuration served by the Render API.
BANNER = {
    "enabled": True,
    "text": "Stumble Rewald v1.0 Mob",
    "subtext": "by:zpedrox e pasin",
    "titleColor": "#00E5FF",
    "subtitleColor": "#39FF14",
    "alignment": "center",
    "position": "top",
    "showInAllRounds": True,
    "showInAllMaps": True,
}


def now():
    return datetime.now(timezone.utc).isoformat()


def response(data=None, status=200, **extra):
    payload = {"success": status < 400, "timestamp": now()}
    if data is not None:
        payload["data"] = data
    payload.update(extra)
    return jsonify(payload), status


def bearer_ok():
    if API_TOKEN == "change-this-in-render":
        return True  # Development mode; set API_TOKEN in Render for production.
    supplied = request.headers.get("Authorization", "")
    return secrets.compare_digest(supplied, f"Bearer {API_TOKEN}")


def optional_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not bearer_ok():
            return response(status=401, error="Unauthorized")
        return func(*args, **kwargs)
    return wrapper


def body():
    return request.get_json(silent=True) or {}


def player_for(user_id):
    user_id = str(user_id or "guest")
    if user_id not in players:
        players[user_id] = {
            "userId": user_id,
            "id": user_id,
            "displayName": ".gg/sgrewald",
            "username": ".gg/sgrewald",
            "coins": 0,
            "crowns": 0,
            "trophies": 0,
            "experience": 0,
            "inventory": [],
            "rewards": [],
            "createdAt": now(),
            "updatedAt": now(),
        }
    return players[user_id]


@app.after_request
def cors_headers(result):
    result.headers["Access-Control-Allow-Origin"] = "*"
    result.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    result.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    return result


@app.route("/", methods=["GET", "HEAD"])
def index():
    return response({"service": SERVICE_NAME, "environment": ENVIRONMENT, "status": "online"})


@app.get("/status")
def status():
    return response({"node": SERVICE_NAME, "env": ENVIRONMENT, "host": request.host, "status": "online"})


@app.get("/health")
def health():
    return response({"status": "ok", "database": "memory", "photon": "not-included"})


@app.post("/api/v1/login")
@app.post("/api/login")
@app.post("/login")
def login():
    data = body()
    user_id = str(data.get("userId") or data.get("user_id") or data.get("deviceId") or uuid.uuid4().hex)
    player = player_for(user_id)
    if data.get("displayName") or data.get("username"):
        player["displayName"] = str(data.get("displayName") or data.get("username"))[:24]
        player["username"] = player["displayName"]
    return response({"token": API_TOKEN, "accessToken": API_TOKEN, "user": player, "player": player}, loggedIn=True)


@app.get("/api/v1/player/<user_id>")
@app.get("/api/player/<user_id>")
@app.get("/user/<user_id>")
@optional_auth
def get_player(user_id):
    return response(player_for(user_id))


@app.put("/api/v1/player/<user_id>")
@app.patch("/api/v1/player/<user_id>")
@optional_auth
def update_player(user_id):
    p = player_for(user_id)
    data = body()
    for source, target in (("displayName", "displayName"), ("username", "username"), ("coins", "coins"), ("crowns", "crowns"), ("trophies", "trophies"), ("experience", "experience")):
        if source in data:
            p[target] = data[source]
    p["updatedAt"] = now()
    return response(p)


@app.get("/api/v1/banner")
@app.get("/api/banner")
@app.get("/banner")
def banner():
    return response(BANNER)


@app.get("/api/v1/config")
@app.get("/api/config")
@app.get("/config")
@optional_auth
def config():
    return response({
        "environment": ENVIRONMENT,
        "backendUrl": request.host_url.rstrip("/"),
        "features": {"customRooms": True, "blockDashRevive": True, "blockDashLegendaryRevive": True},
        "matchmaking": {"enabled": True, "provider": "local-test"},
    })


@app.route("/api/v1/profile", methods=["GET", "POST"])
@app.route("/profile", methods=["GET", "POST"])
@optional_auth
def profile():
    data = body()
    return response(player_for(data.get("userId") or request.args.get("userId") or "guest"))


@app.route("/api/v1/inventory", methods=["GET", "POST", "PUT"])
@app.route("/inventory", methods=["GET", "POST", "PUT"])
@optional_auth
def inventory():
    data = body()
    p = player_for(data.get("userId") or request.args.get("userId") or "guest")
    if request.method != "GET" and data.get("itemId"):
        p["inventory"].append({"itemId": str(data["itemId"]), "equipped": bool(data.get("equipped", False))})
    return response({"items": p["inventory"], "balances": {"coins": p["coins"], "crowns": p["crowns"]}})


@app.route("/api/v1/ranks", methods=["GET", "POST"])
@app.route("/api/v1/ranking", methods=["GET", "POST"])
@app.route("/ranking", methods=["GET", "POST"])
@optional_auth
def ranks():
    rows = sorted(players.values(), key=lambda p: int(p.get("trophies", 0)), reverse=True)
    start = int(request.args.get("start", 0))
    count = int(request.args.get("count", 100))
    return response({"entries": rows[start:start + count], "total": len(rows)})


@app.route("/api/v1/news", methods=["GET", "POST"])
@app.route("/news", methods=["GET", "POST"])
@optional_auth
def news():
    return response({"items": [], "latestNewsId": 0})


@app.route("/api/v1/economy", methods=["GET", "POST"])
@app.route("/economy", methods=["GET", "POST"])
@app.route("/api/v1/refresh-economy", methods=["GET", "POST"])
@optional_auth
def economy():
    p = player_for(body().get("userId") or request.args.get("userId") or "guest")
    return response({"balances": {"coins": p["coins"], "crowns": p["crowns"]}, "rewards": p["rewards"]})


@app.route("/api/v1/purchase", methods=["POST"])
@app.route("/purchase", methods=["POST"])
@app.route("/api/v1/purchase-drop", methods=["POST"])
@app.route("/api/v1/purchase-gacha", methods=["POST"])
@optional_auth
def purchase():
    return response({"purchaseId": uuid.uuid4().hex, "completed": True, "item": body().get("itemId")})


@app.route("/api/v1/pass", methods=["GET", "POST"])
@app.route("/api/v1/pass/reward", methods=["GET", "POST"])
@app.route("/api/v1/pass/tier", methods=["GET", "POST"])
@optional_auth
def battle_pass():
    return response({"active": True, "tier": 0, "rewards": [], "claimed": []})


@app.route("/api/v1/search-users", methods=["GET", "POST"])
@app.route("/api/v1/users/search", methods=["GET", "POST"])
@optional_auth
def search_users():
    query = str(body().get("query") or request.args.get("query") or "").lower()
    found = [p for p in players.values() if query in p["displayName"].lower()]
    return response({"users": found[:50]})


@app.route("/api/v1/finish-round", methods=["POST"])
@app.route("/api/v1/finish-tournament-round", methods=["POST"])
@app.route("/api/v1/check-players", methods=["GET", "POST"])
@app.route("/api/v1/round/finish", methods=["POST"])
@optional_auth
def finish_round():
    return response({"accepted": True, "finished": True, "rewards": []})


@app.route("/api/v1/rooms", methods=["GET", "POST"])
@app.route("/api/v1/matchmaking", methods=["GET", "POST"])
@app.route("/matchmaking", methods=["GET", "POST"])
@optional_auth
def matchmaking():
    data = body()
    room_id = str(data.get("roomId") or data.get("roomCode") or uuid.uuid4().hex[:8].upper())
    rooms.setdefault(room_id, {"roomId": room_id, "status": "waiting", "players": [], "map": data.get("map", "BlockDash")})
    return response(rooms[room_id])


# Compatibility fallback: every other HTTP API path receives valid JSON instead of HTML.
# It cannot implement Photon binary matchmaking; a real Photon server is still required for that.
@app.route("/<path:unknown>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
def api_fallback(unknown):
    if request.method == "OPTIONS":
        return ("", 204)
    return response({"route": "/" + unknown, "implemented": False, "service": SERVICE_NAME}, status=200)


@app.errorhandler(404)
def not_found(_error):
    return response(status=404, error="Route not found")


@app.errorhandler(500)
def server_error(_error):
    return response(status=500, error="Internal server error")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))


    




