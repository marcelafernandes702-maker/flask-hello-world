from datetime import datetime, timezone
from secrets import token_urlsafe
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field


app = FastAPI(
    title="LEBS Stumble Backend",
    description="Test backend for Stumble Guys 0.50",
    version="0.50.0",
)

# In-memory test database. Data is lost when the server restarts.
users = {}
tokens = {}


BOOTSTRAP = {
    "gameVersion": "0.50",
    "backendVersion": "LEBS-0.50",
    "maintenance": False,
    "services": {
        "login": "/api/user/login",
        "config": "/api/config",
        "inventory": "/api/user/inventory/selection",
        "photon": "/api/photon/config",
    },
}


CONFIG = {
    "gameVersion": "0.50",
    "region": "sa",
    "features": {
        "inventory": True,
        "profile": True,
        "photonRealtime": True,
    },
    "photon": {
        "enabled": True,
        "appId": "6fe8305a-ef22-40f2-9c0e-3052a8adec0d",
        "region": "sa",
        "regions": "sa;us;usw;eu",
    },
}


class LoginRequest(BaseModel):
    userId: Optional[str] = None
    playerId: Optional[str] = None
    player: Optional[dict] = None
    profile: Optional[dict] = None


class SelectionRequest(BaseModel):
    userId: Optional[str] = None
    playerId: Optional[str] = None
    player: Optional[dict] = None
    profile: Optional[dict] = None
    data: Optional[dict] = None
    selection: dict = Field(default_factory=dict)


def get_user(access_token: Optional[str]):
    if not access_token or access_token not in tokens:
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid accessToken",
        )

    uid = tokens[access_token]
    return users[uid]


@app.get("/api/bootstrap")
@app.get("/bootstrap")
def bootstrap():
    return {
        "result": "success",
        "data": BOOTSTRAP,
    }


@app.get("/api/config")
@app.get("/config")
def config():
    return {
        "result": "success",
        "data": CONFIG,
    }


@app.get("/api/photon/config")
def photon_config():
    return {
        "result": "success",
        "photon": CONFIG["photon"],
    }


@app.post("/user/login")
@app.post("/api/user/login")
@app.post("/api/v1/user/login")
def login(body: LoginRequest):
    uid = body.userId or body.playerId or "player_" + token_urlsafe(8)

    if uid not in users:
        users[uid] = {
            "userId": uid,
            "playerId": uid,
            "player": body.player or {
                "name": "Player",
                "level": 1,
                "trophies": 0,
            },
            "profile": body.profile or {
                "nickname": "Player",
                "createdAt": datetime.now(timezone.utc).isoformat(),
            },
            "inventory": {
                "skin": None,
                "emote": None,
                "footsteps": None,
                "victoryAnimation": None,
            },
        }

    access_token = token_urlsafe(32)
    tokens[access_token] = uid

    return {
        "result": "success",
        "accessToken": access_token,
        "userId": uid,
        "playerId": uid,
        "player": users[uid]["player"],
        "profile": users[uid]["profile"],
        "data": users[uid],
    }


@app.post("/user/inventory/selection")
@app.post("/api/user/inventory/selection")
@app.post("/api/v1/user/inventory/selection")
def inventory_selection(
    body: SelectionRequest,
    authorization: Optional[str] = Header(default=None),
    accessToken: Optional[str] = None,
):
    # Accept Authorization: Bearer <token>
    # or an accessToken query parameter.
    bearer = None

    if authorization:
        parts = authorization.split(" ", 1)

        if len(parts) == 2 and parts[0].lower() == "bearer":
            bearer = parts[1]

    user = get_user(bearer or accessToken)

    # Update only the inventory categories included in the request.
    for key, value in body.selection.items():
        if key not in user["inventory"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category: {key}",
            )

        user["inventory"][key] = value

    return {
        "result": "success",
        "userId": user["userId"],
        "playerId": user["playerId"],
        "player": user["player"],
        "profile": user["profile"],
        "data": {
            "inventory": user["inventory"],
        },
    }


@app.get("/")
def home():
    return {
        "name": "LEBS STUMBLE BACKEND",
        "version": "0.50",
        "status": "online",
        "docs": "/docs",
    }




















    




