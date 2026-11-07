import os
import secrets
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from werkzeug.security import check_password_hash, generate_password_hash

DB_PATH = os.environ.get("DB_PATH", "data.sqlite3")
PLAYER_ID_MIN = 1000
PLAYER_ID_MAX = 9999

app = FastAPI(
    title="SGTracer Tournament API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = db()

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL UNIQUE,
            username TEXT NOT NULL UNIQUE,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            player_id INTEGER NOT NULL
                REFERENCES players(player_id) ON DELETE CASCADE,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tournaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'open',
            starts_at TEXT,
            ends_at TEXT,
            max_players INTEGER NOT NULL DEFAULT 32,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tournament_players (
            tournament_id INTEGER NOT NULL
                REFERENCES tournaments(id) ON DELETE CASCADE,
            player_id INTEGER NOT NULL
                REFERENCES players(player_id) ON DELETE CASCADE,
            joined_at TEXT NOT NULL,
            PRIMARY KEY (tournament_id, player_id)
        );

        CREATE TABLE IF NOT EXISTS tournament_results (
            tournament_id INTEGER NOT NULL
                REFERENCES tournaments(id) ON DELETE CASCADE,
            player_id INTEGER NOT NULL
                REFERENCES players(player_id) ON DELETE CASCADE,
            points INTEGER NOT NULL DEFAULT 0,
            position INTEGER,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (tournament_id, player_id)
        );
        """
    )

    conn.commit()
    conn.close()


@app.on_event("startup")
def startup():
    init_db()


class RegisterIn(BaseModel):
    email: Optional[str] = None
    password: str = Field(min_length=4)


class TournamentIn(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    status: str = "open"
    startsAt: Optional[str] = None
    endsAt: Optional[str] = None
    maxPlayers: int = Field(default=32, ge=2, le=10000)


class ResultIn(BaseModel):
    points: int = 0
    position: Optional[int] = None


class TournamentPatch(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    startsAt: Optional[str] = None
    endsAt: Optional[str] = None
    maxPlayers: Optional[int] = Field(
        default=None,
        ge=2,
        le=10000,
    )


def player_json(row):
    return {
        "playerID": row["player_id"],
        "username": row["username"],
        "email": row["email"],
        "createdAt": row["created_at"],
    }


def next_player_id(conn):
    used = {
        row[0]
        for row in conn.execute(
            "SELECT player_id FROM players"
        ).fetchall()
    }

    total = PLAYER_ID_MAX - PLAYER_ID_MIN + 1

    if len(used) >= total:
        raise HTTPException(
            status_code=503,
            detail="Todos os playerIDs de 1000 a 9999 estão ocupados",
        )

    candidate = (
        secrets.randbelow(total)
        + PLAYER_ID_MIN
    )

    while candidate in used:
        if candidate == PLAYER_ID_MAX:
            candidate = PLAYER_ID_MIN
        else:
            candidate += 1

    return candidate


def auth_player(authorization: Optional[str]):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Use Authorization: Bearer <token>",
        )

    token = authorization[7:].strip()

    conn = db()

    row = conn.execute(
        """
        SELECT p.*
        FROM players p
        JOIN sessions s ON s.player_id = p.player_id
        WHERE s.token = ?
        """,
        (token,),
    ).fetchone()

    conn.close()

    if row is None:
        raise HTTPException(
            status_code=401,
            detail="Token inválido",
        )

    return row


@app.get("/")
def root():
    return {
        "service": "SGTracer Tournament API",
        "status": "online",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {
        "ok": True,
        "time": now(),
    }


@app.post("/auth/register", status_code=201)
def register(payload: RegisterIn):
    conn = db()

    email = (
        payload.email.strip().lower()
        if payload.email
        else None
    )

    try:
        player_id = next_player_id(conn)

        username = (
            f".gg/sgtracer<sup>{player_id}"
        )

        conn.execute(
            """
            INSERT INTO players(
                player_id,
                username,
                email,
                password_hash,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                player_id,
                username,
                email,
                generate_password_hash(payload.password),
                now(),
            ),
        )

        conn.commit()

        row = conn.execute(
            "SELECT * FROM players WHERE player_id = ?",
            (player_id,),
        ).fetchone()

        return {
            "player": player_json(row),
            "message": "Jogador criado",
        }

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Esse email já está cadastrado",
        )

    finally:
        conn.close()


@app.post("/auth/login")
def login(payload: RegisterIn):
    conn = db()

    email = (
        payload.email.strip().lower()
        if payload.email
        else ""
    )

    row = conn.execute(
        "SELECT * FROM players WHERE email = ?",
        (email,),
    ).fetchone()

    if row is None or not check_password_hash(
        row["password_hash"],
        payload.password,
    ):
        conn.close()

        raise HTTPException(
            status_code=401,
            detail="Email ou senha inválidos",
        )

    token = secrets.token_urlsafe(32)

    conn.execute(
        """
        INSERT INTO sessions(
            token,
            player_id,
            created_at
        )
        VALUES (?, ?, ?)
        """,
        (
            token,
            row["player_id"],
            now(),
        ),
    )

    conn.commit()
    conn.close()

    return {
        "token": token,
        "player": player_json(row),
    }


@app.get("/players/me")
def me(
    authorization: Optional[str] = Header(None),
):
    player = auth_player(authorization)

    return {
        "player": player_json(player),
    }


@app.get("/tournaments")
def list_tournaments(
    status: Optional[str] = None,
):
    conn = db()

    if status:
        rows = conn.execute(
            """
            SELECT *
            FROM tournaments
            WHERE status = ?
            ORDER BY id DESC
            """,
            (status,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT *
            FROM tournaments
            ORDER BY id DESC
            """
        ).fetchall()

    tournaments = []

    for row in rows:
        item = dict(row)

        item["players"] = conn.execute(
            """
            SELECT COUNT(*)
            FROM tournament_players
            WHERE tournament_id = ?
            """,
            (row["id"],),
        ).fetchone()[0]

        tournaments.append(item)

    conn.close()

    return {
        "tournaments": tournaments,
    }


@app.post("/tournaments", status_code=201)
def create_tournament(
    payload: TournamentIn,
    authorization: Optional[str] = Header(None),
):
    auth_player(authorization)

    conn = db()

    cursor = conn.execute(
        """
        INSERT INTO tournaments(
            name,
            description,
            status,
            starts_at,
            ends_at,
            max_players,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.name,
            payload.description,
            payload.status,
            payload.startsAt,
            payload.endsAt,
            payload.maxPlayers,
            now(),
        ),
    )

    conn.commit()

    row = conn.execute(
        "SELECT * FROM tournaments WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()

    conn.close()

    return {
        "tournament": dict(row),
    }


@app.get("/tournaments/{tournament_id}")
def get_tournament(tournament_id: int):
    conn = db()

    tournament = conn.execute(
        """
        SELECT *
        FROM tournaments
        WHERE id = ?
        """,
        (tournament_id,),
    ).fetchone()

    if tournament is None:
        conn.close()

        raise HTTPException(
            status_code=404,
            detail="Torneio não encontrado",
        )

    players = conn.execute(
        """
        SELECT
            p.player_id AS playerID,
            p.username,
            tp.joined_at AS joinedAt
        FROM tournament_players tp
        JOIN players p
            ON p.player_id = tp.player_id
        WHERE tp.tournament_id = ?
        ORDER BY tp.joined_at
        """,
        (tournament_id,),
    ).fetchall()

    conn.close()

    return {
        "tournament": dict(tournament),
        "players": [dict(player) for player in players],
    }


@app.post("/tournaments/{tournament_id}/join")
def join_tournament(
    tournament_id: int,
    authorization: Optional[str] = Header(None),
):
    player = auth_player(authorization)

    conn = db()

    tournament = conn.execute(
        """
        SELECT *
        FROM tournaments
        WHERE id = ?
        """,
        (tournament_id,),
    ).fetchone()

    if tournament is None:
        conn.close()

        raise HTTPException(
            status_code=404,
            detail="Torneio não encontrado",
        )

    if tournament["status"] != "open":
        conn.close()

        raise HTTPException(
            status_code=400,
            detail="Esse torneio não está aberto",
        )

    count = conn.execute(
        """
        SELECT COUNT(*)
        FROM tournament_players
        WHERE tournament_id = ?
        """,
        (tournament_id,),
    ).fetchone()[0]

    if count >= tournament["max_players"]:
        conn.close()

        raise HTTPException(
            status_code=400,
            detail="O torneio está lotado",
        )

    try:
        conn.execute(
            """
            INSERT INTO tournament_players(
                tournament_id,
                player_id,
                joined_at
            )
            VALUES (?, ?, ?)
            """,
            (
                tournament_id,
                player["player_id"],
                now(),
            ),
        )

        conn.commit()

    except sqlite3.IntegrityError:
        conn.close()

        raise HTTPException(
            status_code=409,
            detail="O jogador já está inscrito",
        )

    conn.close()

    return {
        "message": "Inscrição realizada",
        "tournamentID": tournament_id,
        "playerID": player["player_id"],
    }


@app.post("/tournaments/{tournament_id}/results")
def submit_result(
    tournament_id: int,
    payload: ResultIn,
    authorization: Optional[str] = Header(None),
):
    player = auth_player(authorization)

    conn = db()

    tournament = conn.execute(
        """
        SELECT id
        FROM tournaments
        WHERE id = ?
        """,
        (tournament_id,),
    ).fetchone()

    if tournament is None:
        conn.close()

        raise HTTPException(
            status_code=404,
            detail="Torneio não encontrado",
        )

    joined = conn.execute(
        """
        SELECT 1
        FROM tournament_players
        WHERE tournament_id = ?
        AND player_id = ?
        """,
        (
            tournament_id,
            player["player_id"],
        ),
    ).fetchone()

    if joined is None:
        conn.close()

        raise HTTPException(
            status_code=400,
            detail="O jogador precisa estar inscrito no torneio",
        )

    conn.execute(
        """
        INSERT INTO tournament_results(
            tournament_id,
            player_id,
            points,
            position,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(tournament_id, player_id)
        DO UPDATE SET
            points = excluded.points,
            position = excluded.position,
            updated_at = excluded.updated_at
        """,
        (
            tournament_id,
            player["player_id"],
            payload.points,
            payload.position,
            now(),
        ),
    )

    conn.commit()
    conn.close()

    return {
        "message": "Resultado salvo",
    }


@app.get("/tournaments/{tournament_id}/ranking")
def ranking(tournament_id: int):
    conn = db()

    rows = conn.execute(
        """
        SELECT
            r.player_id AS playerID,
            p.username,
            r.points,
            r.position,
            r.updated_at AS updatedAt
        FROM tournament_results r
        JOIN players p
            ON p.player_id = r.player_id
        WHERE r.tournament_id = ?
        ORDER BY
            r.points DESC,
            r.position ASC,
            r.updated_at ASC
        """,
        (tournament_id,),
    ).fetchall()

    conn.close()

    return {
        "tournamentID": tournament_id,
        "ranking": [dict(row) for row in rows],
    }


@app.patch("/tournaments/{tournament_id}")
def update_tournament(
    tournament_id: int,
    payload: TournamentPatch,
    authorization: Optional[str] = Header(None),
):
    auth_player(authorization)

    values = payload.dict(exclude_none=True)

    values = {
        "starts_at" if key == "startsAt"
        else "ends_at" if key == "endsAt"
        else "max_players" if key == "maxPlayers"
        else key: value
        for key, value in values.items()
    }

    if not values:
        raise HTTPException(
            status_code=400,
            detail="Nenhum campo válido para atualizar",
        )

    conn = db()

    exists = conn.execute(
        """
        SELECT 1
        FROM tournaments
        WHERE id = ?
        """,
        (tournament_id,),
    ).fetchone()

    if exists is None:
        conn.close()

        raise HTTPException(
            status_code=404,
            detail="Torneio não encontrado",
        )

    assignments = ", ".join(
        f"{key} = ?"
        for key in values
    )

    conn.execute(
        f"""
        UPDATE tournaments
        SET {assignments}
        WHERE id = ?
        """,
        list(values.values()) + [tournament_id],
    )

    conn.commit()
    conn.close()

    return {
        "message": "Torneio atualizado",
    }


if __name__ == "__main__":
    import uvicorn

    init_db()

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
    )






























    




