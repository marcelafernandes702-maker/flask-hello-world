import logging
import os
import random
import secrets
import sqlite3
import time

from flask import Flask, g, jsonify, request
from werkzeug.exceptions import HTTPException

# ============ CONFIG ============
APP_NAME = "Stumble Lend"
APP_VERSION = "0.50"
NAME_PREFIX = ".gg/sglend"
TOURNAMENT_ID = 1
TOURNAMENT_NAME = "Lend BD 1v1"
QUEUE_TIMEOUT = 60  # segundos na fila antes de expirar
DB_PATH = os.environ.get("DB_PATH", "stumble_lend.db")

SUP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
UNSUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("stumble-lend")

app = Flask(__name__)
app.json.ensure_ascii = False
app.json.sort_keys = False


# ============ BANCO ============
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, timeout=10)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT UNIQUE NOT NULL,
            name TEXT UNIQUE NOT NULL,
            token TEXT UNIQUE NOT NULL,
            transferred INTEGER NOT NULL DEFAULT 0,
            wins INTEGER NOT NULL DEFAULT 0,
            losses INTEGER NOT NULL DEFAULT 0,
            created_at REAL NOT NULL,
            last_login REAL
        );
        CREATE TABLE IF NOT EXISTS queue (
            player_id INTEGER PRIMARY KEY,
            joined_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            p1 INTEGER NOT NULL,
            p2 INTEGER NOT NULL,
            winner INTEGER,
            created_at REAL NOT NULL
        );
        """
    )
    db.commit()
    db.close()


# ============ HELPERS ============
def new_name(db):
    """.gg/sglend + números em sobrescrito, sem repetir."""
    for _ in range(50):
        name = NAME_PREFIX + str(random.randint(100, 99999)).translate(SUP)
        if not db.execute("SELECT 1 FROM players WHERE name=?", (name,)).fetchone():
            return name
    return NAME_PREFIX + str(int(time.time())).translate(SUP)


def name_html(name):
    return f"{NAME_PREFIX}<sup>{name[len(NAME_PREFIX):].translate(UNSUP)}</sup>"


def body():
    return request.get_json(silent=True) or {}


def pick(data, *keys):
    for k in keys:
        v = data.get(k)
        if v not in (None, ""):
            return str(v).strip()
    return ""


def current_player():
    token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    token = token or request.headers.get("X-Token", "").strip() or pick(body(), "token")
    if not token:
        return None
    return get_db().execute("SELECT * FROM players WHERE token=?", (token,)).fetchone()


def err(msg, code=400, **extra):
    return jsonify(ok=False, error=msg, **extra), code


def player_json(p):
    return {
        "id": p["id"],
        "name": p["name"],
        "name_html": name_html(p["name"]),
        "wins": p["wins"],
        "losses": p["losses"],
    }


def popup_json(transferred):
    return {
        "show": not transferred,
        "type": "transfer_items",
        "title": "Transferir elementos",
        "message": "Transfira seus elementos para entrar no lobby.",
        "confirm_endpoint": "/api/transfer/confirm",
    }


def clean_queue(db):
    db.execute("DELETE FROM queue WHERE joined_at < ?", (time.time() - QUEUE_TIMEOUT,))


@app.after_request
def no_cache(resp):
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.errorhandler(HTTPException)
def http_error(e):
    return err(e.name.lower().replace(" ", "_"), e.code)


@app.errorhandler(Exception)
def server_error(e):
    log.exception("erro interno")
    return err("internal_error", 500)


# ============ ROTAS INFO ============
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
        tournament={"id": TOURNAMENT_ID, "name": TOURNAMENT_NAME, "mode": "1v1"},
        player_name_prefix=NAME_PREFIX,
        login_on_loading_screen=True,
        transfer_required=True,
    )


@app.get("/api/version")
def version():
    return jsonify(name=APP_NAME, version=APP_VERSION)


@app.get("/api/status")
def status():
    db = get_db()
    clean_queue(db)
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


# ============ LOGIN / LOBBY ============
@app.post("/api/user/login")
@app.post("/api/login")
def login():
    data = body()
    device_id = pick(data, "device_id", "deviceId", "uid", "id")
    client_version = pick(data, "version", "app_version") or request.headers.get("X-Version", APP_VERSION)

    if not device_id:
        return err("device_id obrigatório", 400)
    if client_version != APP_VERSION:
        return err(f"Versão inválida. Use a {APP_VERSION}", 426)

    db = get_db()
    now = time.time()
    p = db.execute("SELECT * FROM players WHERE device_id=?", (device_id,)).fetchone()
    first_login = p is None

    if first_login:
        db.execute(
            "INSERT INTO players (device_id, name, token, created_at, last_login) VALUES (?,?,?,?,?)",
            (device_id, new_name(db), secrets.token_hex(24), now, now),
        )
        log.info("novo jogador device=%s", device_id[:8])
    else:
        db.execute("UPDATE players SET last_login=? WHERE id=?", (now, p["id"]))
    db.commit()
    p = db.execute("SELECT * FROM players WHERE device_id=?", (device_id,)).fetchone()

    return jsonify(
        ok=True,
        first_login=first_login,
        token=p["token"],
        player=player_json(p),
        popup=popup_json(bool(p["transferred"])),
        can_enter_lobby=bool(p["transferred"]),
    )


@app.get("/api/user/me")
def me():
    p = current_player()
    if not p:
        return err("unauthorized", 401)
    return jsonify(ok=True, player=player_json(p), can_enter_lobby=bool(p["transferred"]))


@app.post("/api/transfer/confirm")
def transfer_confirm():
    p = current_player()
    if not p:
        return err("unauthorized", 401)
    db = get_db()
    db.execute("UPDATE players SET transferred=1 WHERE id=?", (p["id"],))
    db.commit()
    return jsonify(ok=True, can_enter_lobby=True)


@app.post("/api/lobby/enter")
def lobby_enter():
    p = current_player()
    if not p:
        return err("unauthorized", 401)
    if not p["transferred"]:
        return err("transfer_required", 403, popup=popup_json(False))
    return jsonify(
        ok=True,
        lobby={"name": APP_NAME, "version": APP_VERSION, "tournament": TOURNAMENT_NAME},
        player=player_json(p),
    )


# ============ TORNEIO ============
@app.get("/api/tournaments")
def tournaments():
    db = get_db()
    clean_queue(db)
    waiting = db.execute("SELECT COUNT(*) c FROM queue").fetchone()["c"]
    return jsonify(
        tournaments=[
            {"id": TOURNAMENT_ID, "name": TOURNAMENT_NAME, "mode": "1v1", "players_waiting": waiting}
        ]
    )















    




