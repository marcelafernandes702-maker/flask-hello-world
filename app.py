import os
import random
import secrets
import sqlite3
import time

from flask import Flask, jsonify, request, g

APP_NAME = "Stumble Lend"
APP_VERSION = "0.50"
NAME_PREFIX = ".gg/sglend"
TOURNAMENT_NAME = "Lend BD 1v1"
DB_PATH = os.environ.get("DB_PATH", "stumble_lend.db")

SUPERSCRIPT = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
app.json.ensure_ascii = False


# ---------- Banco de dados ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            token TEXT NOT NULL,
            transferred INTEGER DEFAULT 0,
            created_at REAL
        );
        CREATE TABLE IF NOT EXISTS queue (
            player_id INTEGER PRIMARY KEY,
            joined_at REAL
        );
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            p1 INTEGER, p2 INTEGER, created_at REAL
        );
        """
    )
    db.commit()
    db.close()


# ---------- Helpers ----------
def make_player_name():
    """.gg/sglend + números em sobrescrito (<sup>)"""
    digits = str(random.randint(100, 99999))
    return f"{NAME_PREFIX}{digits.translate(SUPERSCRIPT)}"


def name_html(name):
    """Versão HTML usando <sup>, caso o cliente suporte rich text."""
    base = name[: len(NAME_PREFIX)]
    sup = name[len(NAME_PREFIX):].translate(str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789"))
    return f"{base}<sup>{sup}</sup>"


def auth_player():
    token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    if not token:
        token = (request.get_json(silent=True) or {}).get("token", "")
    if not token:
        return None
    return get_db().execute("SELECT * FROM players WHERE token=?", (token,)).fetchone()


def unauthorized():
    return jsonify(ok=False, error="unauthorized"), 401


# ---------- Rotas ----------
@app.get("/")
def index():
    return jsonify(name=APP_NAME, version=APP_VERSION, status="online")


@app.get("/health")
def health():
    return "ok", 200


@app.get("/api/config")
def config():
    return jsonify(
        name=APP_NAME,
        version=APP_VERSION,
        tournament=TOURNAMENT_NAME,
        login_on_loading_screen=True,
    )


@app.get("/api/version")
def version():
    return jsonify(name=APP_NAME, version=APP_VERSION)


@app.get("/api/status")
def status():
    db = get_db()
    players = db.execute("SELECT COUNT(*) c FROM players").fetchone()["c"]
    waiting = db.execute("SELECT COUNT(*) c FROM queue").fetchone()["c"]
    return jsonify(
        ok=True,
        status="online",
        name=APP_NAME,
        version=APP_VERSION,
        tournament=TOURNAMENT_NAME,
        players_registered=players,
        players_waiting=waiting,
        server_time=int(time.time()),
    )


@app.post("/api/login")
@app.post("/api/user/login")
def login():
    """Chamado na tela de carregamento. Cria a conta no primeiro acesso."""
    data = request.get_json(silent=True) or {}
    device_id = (data.get("device_id") or "").strip()
    client_version = str(data.get("version", APP_VERSION))

    if not device_id:
        return jsonify(ok=False, error="device_id obrigatório"), 400
    if client_version != APP_VERSION:
        return jsonify(ok=False, error=f"Versão inválida. Use a {APP_VERSION}"), 426

    db = get_db()
    player = db.execute("SELECT * FROM players WHERE device_id=?", (device_id,)).fetchone()
    first_login = player is None

    if first_login:
        db.execute(
            "INSERT INTO players (device_id, name, token, created_at) VALUES (?,?,?,?)",
            (device_id, make_player_name(), secrets.token_hex(24), time.time()),
        )
        db.commit()
        player = db.execute("SELECT * FROM players WHERE device_id=?", (device_id,)).fetchone()

    # Pop-up de transferir elementos: aparece até o jogador confirmar
    show_transfer_popup = not bool(player["transferred"])

    return jsonify(
        ok=True,
        first_login=first_login,
        token=player["token"],
        player={
            "id": player["id"],
            "name": player["name"],
            "name_html": name_html(player["name"]),
        },
        popup={
            "show": show_transfer_popup,
            "type": "transfer_items",
            "title": "Transferir elementos",
            "message": "Transfira seus elementos para entrar no lobby.",
            "confirm_endpoint": "/api/transfer/confirm",
        },
        can_enter_lobby=not show_transfer_popup,
    )


@app.post("/api/transfer/confirm")
def transfer_confirm():
    player = auth_player()
    if not player:
        return unauthorized()
    db = get_db()
    db.execute("UPDATE players SET transferred=1 WHERE id=?", (player["id"],))
    db.commit()
    return jsonify(ok=True, can_enter_lobby=True)


@app.post("/api/lobby/enter")
def lobby_enter():
    player = auth_player()
    if not player:
        return unauthorized()
    if not player["transferred"]:
        return jsonify(ok=False, error="transfer_required", popup="transfer_items"), 403
    return jsonify(
        ok=True,
        lobby={"name": APP_NAME, "version": APP_VERSION, "tournament": TOURNAMENT_NAME},
    )


@app.get("/api/tournaments")
def tournaments():
    count = get_db().execute("SELECT COUNT(*) c FROM queue").fetchone()["c"]
    return jsonify(
        tournaments=[
            {"id": 1, "name": TOURNAMENT_NAME, "mode": "1v1", "players_waiting": count}
        ]
    )


@app.post("/api/tournaments/1/join")
def tournament_join():
    player = auth_player()
    if not player:
        return unauthorized()
    if not player["transferred"]:
        return jsonify(ok=False, error="transfer_required"), 403

    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO queue (player_id, joined_at) VALUES (?,?)",
        (player["id"], time.time()),
    )
    opponent = db.execute(
        "SELECT q.player_id, p.name FROM queue q JOIN players p ON p.id=q.player_id "
        "WHERE q.player_id != ? ORDER BY q.joined_at LIMIT 1",
        (player["id"],),
    ).fetchone()

    if opponent:
        db.execute("DELETE FROM queue WHERE player_id IN (?,?)", (player["id"], opponent["player_id"]))
        cur = db.execute(
            "INSERT INTO matches (p1, p2, created_at) VALUES (?,?,?)",
            (player["id"], opponent["player_id"], time.time()),
        )
        db.commit()
        return jsonify(
            ok=True,
            status="matched",
            match_id=cur.lastrowid,
            tournament=TOURNAMENT_NAME,
            opponent=opponent["name"],
        )

    db.commit()
    return jsonify(ok=True, status="waiting", tournament=TOURNAMENT_NAME)


@app.post("/api/tournaments/1/leave")
def tournament_leave():
    player = auth_player()
    if not player:
        return unauthorized()
    db = get_db()
    db.execute("DELETE FROM queue WHERE player_id=?", (player["id"],))
    db.commit()
    return jsonify(ok=True)


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))















    




