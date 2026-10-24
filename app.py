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
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            token TEXT NOT NULL,
            transferred INTEGER NOT NULL DEFAULT 0,
            wins INTEGER NOT NULL DEFAULT 0,
            losses INTEGER NOT NULL DEFAULT 0,
            created_at REAL NOT NULL DEFAULT 0,
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
            created_at REAL NOT NULL DEFAULT 0
        );
        """
    )
    # Migração: bancos criados pela versão anterior não têm estas colunas
    wanted = {
        "players": {
            "wins": "INTEGER NOT NULL DEFAULT 0",
            "losses": "INTEGER NOT NULL DEFAULT 0",
            "last_login": "REAL",
            "transferred": "INTEGER NOT NULL DEFAULT 0",
        },
        "matches": {"winner": "INTEGER"},
    }
    for table, cols in wanted.items():
        have = {r[1] for r in db.execute(f"PRAGMA table_info({table})")}
        for col, ddl in cols.items():
            if col not in have:
                db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
                log.info("migração: %s.%s adicionada", table, col)
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
    log.exception("erro interno em %s %s", request.method, request.path)
    if os.environ.get("DEBUG_ERRORS") == "1":
        return err("internal_error", 500, detail=f"{type(e).__name__}: {e}")
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
        lobby_name="MainLobby",
        tournament={"id": TOURNAMENT_ID, "name": TOURNAMENT_NAME, "mode": "1v1"},
        player_name_prefix=NAME_PREFIX,
        login_on_loading_screen=True,
        transfer_required=False,
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
        server_ready=True,
        maintenance=False,
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
        can_enter_lobby=True,
    )


@app.get("/api/user/me")
def me():
    p = current_player()
    if not p:
        return err("unauthorized", 401)
    return jsonify(ok=True, player=player_json(p), can_enter_lobby=True)


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


@app.post(f"/api/tournaments/{TOURNAMENT_ID}/join")
def tournament_join():
    p = current_player()
    if not p:
        return err("unauthorized", 401)

    db = get_db()
    clean_queue(db)
    opp = db.execute(
        "SELECT q.player_id, pl.name FROM queue q JOIN players pl ON pl.id=q.player_id "
        "WHERE q.player_id != ? ORDER BY q.joined_at LIMIT 1",
        (p["id"],),
    ).fetchone()

    if opp:
        db.execute("DELETE FROM queue WHERE player_id IN (?,?)", (p["id"], opp["player_id"]))
        cur = db.execute(
            "INSERT INTO matches (p1, p2, created_at) VALUES (?,?,?)",
            (opp["player_id"], p["id"], time.time()),
        )
        db.commit()
        return jsonify(
            ok=True, status="matched", match_id=cur.lastrowid,
            tournament=TOURNAMENT_NAME, opponent=opp["name"],
        )

    db.execute("INSERT OR REPLACE INTO queue (player_id, joined_at) VALUES (?,?)", (p["id"], time.time()))
    db.commit()
    return jsonify(ok=True, status="waiting", tournament=TOURNAMENT_NAME)


@app.post(f"/api/tournaments/{TOURNAMENT_ID}/leave")
def tournament_leave():
    p = current_player()
    if not p:
        return err("unauthorized", 401)
    db = get_db()
    db.execute("DELETE FROM queue WHERE player_id=?", (p["id"],))
    db.commit()
    return jsonify(ok=True)


@app.post("/api/matches/<int:match_id>/result")
def match_result(match_id):
    p = current_player()
    if not p:
        return err("unauthorized", 401)
    db = get_db()
    m = db.execute("SELECT * FROM matches WHERE id=?", (match_id,)).fetchone()
    if not m or p["id"] not in (m["p1"], m["p2"]):
        return err("match_not_found", 404)
    if m["winner"] is not None:
        return err("already_reported", 409)

    won = bool(body().get("won"))
    winner = p["id"] if won else (m["p2"] if p["id"] == m["p1"] else m["p1"])
    loser = m["p2"] if winner == m["p1"] else m["p1"]
    db.execute("UPDATE matches SET winner=? WHERE id=?", (winner, match_id))
    db.execute("UPDATE players SET wins=wins+1 WHERE id=?", (winner,))
    db.execute("UPDATE players SET losses=losses+1 WHERE id=?", (loser,))
    db.commit()
    return jsonify(ok=True, winner_id=winner)


@app.get("/api/tournaments/ranking")
def ranking():
    rows = get_db().execute(
        "SELECT name, wins, losses FROM players WHERE wins+losses>0 "
        "ORDER BY wins DESC, losses ASC LIMIT 50"
    ).fetchall()
    return jsonify(
        tournament=TOURNAMENT_NAME,
        ranking=[
            {"position": i + 1, "name": r["name"], "name_html": name_html(r["name"]),
             "wins": r["wins"], "losses": r["losses"]}
            for i, r in enumerate(rows)
        ],
    )


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))















    




