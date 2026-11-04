import json
import logging
import os
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

APP_VERSION = os.getenv("APP_VERSION", "0.45.4")
APP_NAME = os.getenv("APP_NAME", "Stumble Pool")
REGION = os.getenv("REGION", "eu")

PLAYER_ID_POOL = os.getenv(
    "PLAYER_ID_POOL",
    "1793,4406,6742,2355,3385,1212,1020,7778,4404,5505,3303,0102,6767,4455,1555,0405,0607",
).split(",")

PLAYER_ID_POOL = [
    value.strip().zfill(4)
    for value in PLAYER_ID_POOL
    if value.strip()
]

DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
TRANSFER_BYTES = int(69.43 * 1024 * 1024)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)

log = logging.getLogger("stumble-backend")

app = FastAPI(
    title=f"{APP_NAME} Backend",
    version=APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def now():
    return datetime.now(timezone.utc).isoformat()


def load_users():
    try:
        return (
            json.loads(USERS_FILE.read_text(encoding="utf-8"))
            if USERS_FILE.exists()
            else {}
        )
    except Exception:
        log.exception("Falha ao ler users.json")
        return {}


def save_users():
    tmp = USERS_FILE.with_suffix(".tmp")

    tmp.write_text(
        json.dumps(users, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    tmp.replace(USERS_FILE)


users: Dict[str, Dict[str, Any]] = load_users()
sessions: Dict[str, str] = {}


def code(n=4):
    return "".join(
        secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
        for _ in range(n)
    )


def new_name():
    return ".gg/sgpool"


def allocate_player_number():
    used = {
        str(u.get("playerNumber", "")).zfill(4)
        for u in users.values()
        if u.get("playerNumber")
    }

    for number in PLAYER_ID_POOL:
        if number not in used:
            return number

    while True:
        number = f"{secrets.randbelow(10000):04d}"

        if number not in used:
            return number


def player_name(u):
    return f".gg/sgpool{str(u.get('playerNumber', '0000')).zfill(4)}"


def public_user(u):
    name = player_name(u)
    number = str(u.get("playerNumber", "0000")).zfill(4)

    return {
        "id": number,
        "userId": number,
        "playerId": number,
        "stumbleId": number,
        "backendId": u["id"],
        "displayName": name,
        "username": name,
        "name": name,
        "level": u.get("level", 1),
        "trophies": u.get("trophies", 0),
        "crowns": u.get("crowns", 0),
        "selectedSkin": u.get("selectedSkin", "Player_Skin0"),
        "inventory": u.get("inventory", ["Player_Skin0"]),
        "createdAt": u.get("createdAt"),
    }


def transfer(required):
    return {
        "required": required,
        "showOnce": required,
        "title": "Transferir elementos",
        "message": "Atualização necessária!",
        "sizeMb": 69.43,
        "sizeBytes": TRANSFER_BYTES,
        "wifiRecommended": True,
        "progressText": "Transferindo elementos essenciais...",
        "completeText": "Transferência de elementos essenciais concluída!",
        "completion": "Após 100%, conectar ao lobby.",
    }


def auth_user(authorization: Optional[str]):
    if not authorization:
        raise HTTPException(401, "Authorization required")

    token = authorization.removeprefix("Bearer ").strip()
    uid = sessions.get(token)

    if not uid or uid not in users:
        raise HTTPException(401, "Invalid or expired token")

    return users[uid]


class Login(BaseModel):
    deviceId: Optional[str] = None
    device_id: Optional[str] = None
    stumbleId: Optional[str] = None
    stumble_id: Optional[str] = None
    version: Optional[str] = None
    appVersion: Optional[str] = None
    transferCompleted: bool = False


class Invite(BaseModel):
    friendId: Optional[str] = None
    userId: Optional[str] = None
    partyId: Optional[str] = None


class TransferComplete(BaseModel):
    completed: bool = True


class SharedPayload(BaseModel):
    playerId: Optional[str] = None
    userId: Optional[str] = None
    stumbleId: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)

    log.info(
        "%s %s -> %s (%dms)",
        request.method,
        request.url.path,
        response.status_code,
        int((time.perf_counter() - started) * 1000),
    )

    return response


@app.get("/")
def root():
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "status": "online",
        "api": "/api",
    }


@app.get("/onlinecheck")
@app.get("/api/health")
@app.get("/api/healthz")
def health():
    return {
        "ok": True,
        "status": "online",
        "version": APP_VERSION,
        "time": now(),
    }


@app.get("/version")
@app.get("/game/version")
def version():
    return {
        "version": APP_VERSION,
        "appVersion": APP_VERSION,
        "minVersion": APP_VERSION,
        "maintenance": False,
    }


@app.get("/config")
@app.get("/game/config")
@app.get("/api/config")
def config():
    return {
        "version": APP_VERSION,
        "appVersion": APP_VERSION,
        "region": REGION,
        "regions": [REGION],
        "maintenance": False,
        "lobbyUrl": "/lobby",
        "transfer": transfer(False),
    }


@app.get("/servers")
def servers():
    return {
        "servers": [
            {
                "id": "main",
                "region": REGION,
                "status": "online",
                "players": len(users),
            }
        ]
    }


@app.get("/servers/region")
def server_region():
    return {
        "region": REGION,
        "server": "main",
        "status": "online",
    }


def do_login(payload: Login):
    raw = payload.model_dump()

    uid = next(
        (
            str(raw[k]).strip()
            for k in (
                "deviceId",
                "device_id",
                "stumbleId",
                "stumble_id",
            )
            if raw.get(k)
        ),
        "guest-" + secrets.token_hex(8),
    )

    first = uid not in users

    if first:
        users[uid] = {
            "id": uid,
            "playerNumber": allocate_player_number(),
            "displayName": None,
            "level": 1,
            "trophies": 0,
            "crowns": 0,
            "selectedSkin": "Player_Skin0",
            "inventory": ["Player_Skin0"],
            "transferCompleted": False,
            "createdAt": now(),
        }

    u = users[uid]

    if not u.get("playerNumber"):
        u["playerNumber"] = allocate_player_number()

    u["displayName"] = player_name(u)

    if payload.transferCompleted:
        u["transferCompleted"] = True

    save_users()

    token = secrets.token_urlsafe(32)
    sessions[token] = uid
    player = public_user(u)

    return {
        "success": True,
        "ok": True,
        "token": token,
        "accessToken": token,
        "refreshToken": token,
        "userId": u["playerNumber"],
        "playerId": u["playerNumber"],
        "stumbleId": u["playerNumber"],
        "deviceId": uid,
        "user": player,
        "profile": player,
        "player": player,
        "firstLogin": first,
        "transfer": transfer(
            first and not u.get("transferCompleted", False)
        ),
        "next": "/lobby",
    }


@app.post("/user/login")
@app.post("/api/v1/userLogin")
@app.post("/login")
@app.post("/auth/login")
def login(payload: Login):
    return do_login(payload)


@app.post("/register")
def register(payload: Login):
    return do_login(payload)


@app.get("/user/login/health")
def login_health():
    return {
        "ok": True,
        "login": "available",
    }


@app.get("/user/refresh")
@app.post("/user/refresh")
def refresh(authorization: Optional[str] = Header(None)):
    u = auth_user(authorization)

    token = secrets.token_urlsafe(32)
    sessions[token] = u["id"]

    return {
        "success": True,
        "token": token,
        "accessToken": token,
        "user": public_user(u),
    }


@app.get("/user/profile")
@app.get("/api/v1/user/profile")
@app.get("/profile")
def profile(authorization: Optional[str] = Header(None)):
    return {
        "success": True,
        "user": public_user(auth_user(authorization)),
    }


@app.get("/usersettings")
def settings(authorization: Optional[str] = Header(None)):
    u = auth_user(authorization)

    return {
        "success": True,
        "ok": True,
        "userId": u["playerNumber"],
        "settings": {
            "language": "pt-BR",
            "playerNames": True,
            "region": REGION,
        },
    }


@app.get("/user/inventory/selection")
@app.post("/user/inventory/selection")
def inventory(authorization: Optional[str] = Header(None)):
    u = auth_user(authorization)

    items = u.get("inventory", ["Player_Skin0"])
    selected = u.get("selectedSkin", "Player_Skin0")

    return {
        "success": True,
        "ok": True,
        "userId": u["playerNumber"],
        "inventory": items,
        "items": items,
        "selection": {
            "skin": selected,
        },
        "selectedSkin": selected,
    }


@app.get("/shared/{shared_id}/{target_id}")
def shared(shared_id: str, target_id: str):
    safe_target = (
        target_id
        if target_id and target_id.upper() != "NULL"
        else "public"
    )

    return {
        "success": True,
        "ok": True,
        "shared": {
            "id": shared_id,
            "target": safe_target,
            "items": [],
            "players": [],
            "data": {},
        },
    }


@app.post("/assets/transfer/complete")
def transfer_complete(
    body: TransferComplete,
    authorization: Optional[str] = Header(None),
):
    u = auth_user(authorization)

    u["transferCompleted"] = body.completed
    save_users()

    return {
        "success": True,
        "transfer": transfer(False),
        "next": "/lobby",
    }


@app.get("/lobby")
def lobby(authorization: Optional[str] = Header(None)):
    u = auth_user(authorization)

    return {
        "success": True,
        "lobby": {
            "id": "main",
            "region": REGION,
            "status": "online",
            "players": len(users),
            "maxPlayers": 32,
        },
        "player": public_user(u),
        "rooms": [],
        "tournaments": [],
    }


@app.get("/news/getall")
def news():
    return {
        "success": True,
        "news": [],
    }


@app.post("/party/invite")
def invite(
    body: Invite,
    authorization: Optional[str] = Header(None),
):
    u = auth_user(authorization)

    return {
        "success": True,
        "from": u["playerNumber"],
        "to": body.friendId or body.userId,
        "partyId": body.partyId or "main",
    }


@app.post("/pusher/authenticate")
def pusher(authorization: Optional[str] = Header(None)):
    u = auth_user(authorization)

    return {
        "auth": "local",
        "user_id": u["playerNumber"],
        "channel_data": json.dumps({
            "user_id": u["playerNumber"],
        }),
    }


@app.get("/tournaments")
def tournaments():
    return {
        "success": True,
        "tournaments": [],
    }


@app.get("/leaderboard")
def leaderboard():
    return {
        "success": True,
        "entries": [],
    }


@app.get("/shop")
def shop():
    return {
        "success": True,
        "items": [],
    }


@app.get("/events")
def events():
    return {
        "success": True,
        "events": [],
    }


@app.get("/maintenance")
def maintenance():
    return {
        "maintenance": False,
        "message": "",
    }


@app.get("/swagger")
@app.get("/api-docs")
def docs_info():
    return {
        "openapi": "/openapi.json",
        "docs": "/docs",
        "version": APP_VERSION,
    }


@app.get("/swagger.json")
def swagger_json():
    return app.openapi()


@app.get("/routes")
@app.get("/api/routes")
def routes():
    return {
        "routes": sorted({r.path for r in app.routes}),
    }


@app.get("/api")
def api_info():
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "status": "online",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
    )




























    




