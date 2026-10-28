from __future__ import annotations

import os
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


SERVICE_NAME = "Stumble Lend"
GAME_VERSION = "0.50"
BACKEND_VERSION = "LEBS-0.50"

PUBLIC_BASE_URL = os.getenv(
    "PUBLIC_BASE_URL",
    "https://sglend-backend.onrender.com",
).rstrip("/")

PHOTON_APP_ID = "6fe8305a-ef22-40f2-9c0e-3052a8adec0d"
PHOTON_REGIONS = ["sa", "us", "usw", "eu"]
DEFAULT_REGION = "sa"

TOURNAMENTS = [
    "Lend BD 1v1",
    "Lend LD 1v1",
]


app = FastAPI(
    title="LEBS Stumble Backend",
    description="Compatibility backend for Stumble Guys 0.50",
    version="0.50.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


USERS: dict[str, dict[str, Any]] = {}
TOKENS: dict[str, str] = {}
MATCHES: dict[str, dict[str, Any]] = {}
REQUEST_LOG: list[dict[str, Any]] = {}


class FlexibleBody(BaseModel):
    model_config = {"extra": "allow"}

    userId: Optional[str] = None
    playerId: Optional[str] = None
    username: Optional[str] = None
    player: Optional[dict[str, Any]] = None
    profile: Optional[dict[str, Any]] = None
    data: Optional[dict[str, Any]] = None
    selection: dict[str, Any] = Field(default_factory=dict)


def now() -> int:
    return int(time.time())


def photon_data() -> dict[str, Any]:
    return {
        "enabled": True,
        "appId": PHOTON_APP_ID,
        "photonAppId": PHOTON_APP_ID,
        "region": DEFAULT_REGION,
        "photonRegion": DEFAULT_REGION,
        "regions": PHOTON_REGIONS,
        "regionList": PHOTON_REGIONS,
        "appVersion": GAME_VERSION,
    }


def player_data(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "userId": user["id"],
        "playerId": user["id"],
        "username": user["username"],
        "displayName": user["username"],
        "playerName": user["username"],
        "playername": user["username"],
        "name": SERVICE_NAME,
        "version": GAME_VERSION,
        "trophies": user["trophies"],
        "crowns": user["crowns"],
        "coins": user["coins"],
        "gems": user["gems"],
        "createdAt": user["createdAt"],
        "tournamentsname": TOURNAMENTS[0],
        "tournamentsname2": TOURNAMENTS[1],
    }


def create_user(username: str = "") -> dict[str, Any]:
    username = username.strip()[:32] if username else ""

    if not username:
        username = f".gg/sglend{secrets.randbelow(900000) + 100000}"

    user = {
        "id": str(uuid.uuid4()),
        "username": username,
        "trophies": 0,
        "crowns": 0,
        "coins": 5000,
        "gems": 10000,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "inventory": {},
    }

    USERS[user["id"]] = user
    return user


def token_from_request(
    authorization: Optional[str] = None,
    x_auth_token: Optional[str] = None,
    access_token: Optional[str] = None,
    token: Optional[str] = None,
) -> Optional[str]:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()

    return x_auth_token or access_token or token


def get_user_from_token(token: Optional[str]) -> Optional[dict[str, Any]]:
    user_id = TOKENS.get(token or "")
    return USERS.get(user_id or "")


def require_user(
    authorization: Optional[str] = None,
    x_auth_token: Optional[str] = None,
    access_token: Optional[str] = None,
    token: Optional[str] = None,
) -> dict[str, Any]:
    user = get_user_from_token(
        token_from_request(
            authorization,
            x_auth_token,
            access_token,
            token,
        )
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="authentication required",
        )

    return user


def common_config() -> dict[str, Any]:
    return {
        "name": SERVICE_NAME,
        "gameName": SERVICE_NAME,
        "gameVersion": GAME_VERSION,
        "version": GAME_VERSION,
        "backendVersion": BACKEND_VERSION,
        "server": PUBLIC_BASE_URL,
        "apiBaseUrl": PUBLIC_BASE_URL,
        "maintenance": False,
        "defaultRegion": DEFAULT_REGION,
        "bestRegion": True,
        "regions": PHOTON_REGIONS,
        "features": {
            "auth": True,
            "profile": True,
            "inventory": True,
            "matchmaking": True,
            "photonRealtime": True,
        },
        "photon": photon_data(),
        "tournaments": TOURNAMENTS,
        "tournamentsname": TOURNAMENTS[0],
        "tournamentsname2": TOURNAMENTS[1],
    }


@app.middleware("http")
async def request_logger(request: Request, call_next):
    response = await call_next(request)

    REQUEST_LOG.append(
        {
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "timestamp": now(),
        }
    )

    del REQUEST_LOG[:-50]
    return response


@app.get("/")
def home():
    return {
        "ok": True,
        "name": SERVICE_NAME,
        "game": SERVICE_NAME,
        "version": GAME_VERSION,
        "status": "online",
        "health": f"{PUBLIC_BASE_URL}/health",
        "docs": "/docs",
    }


@app.get("/health")
@app.get("/healthz")
@app.get("/api/health")
def health():
    return {
        "ok": True,
        "status": "ok",
        "version": GAME_VERSION,
    }


@app.get("/status")
@app.get("/api/status")
@app.get("/api/v1/status")
def status():
    return {
        "ok": True,
        "status": "online",
        "service": SERVICE_NAME,
        "version": GAME_VERSION,
        "backend": PUBLIC_BASE_URL,
        "timestamp": now(),
    }


@app.get("/config")
@app.get("/api/config")
@app.get("/api/v1/config")
def config():
    settings = common_config()

    return {
        "ok": True,
        "result": "success",
        "data": settings,
        **settings,
    }


@app.get("/bootstrap")
@app.get("/api/bootstrap")
@app.get("/api/v1/bootstrap")
def bootstrap():
    endpoints = {
        "login": "/api/user/login",
        "profile": "/api/profile",
        "inventory": "/api/user/inventory/selection",
        "shared": "/shared/1/NULL",
        "matchmaking": "/api/matchmaking/join",
        "matchmakingFilter": "/api/matchmaking/filter",
        "photon": "/api/photon/config",
    }

    settings = common_config()

    return {
        "ok": True,
        "result": "success",
        "name": SERVICE_NAME,
        "gameVersion": GAME_VERSION,
        "backendVersion": BACKEND_VERSION,
        "maintenance": False,
        "serverTime": now(),
        "endpoints": endpoints,
        "services": endpoints,
        "config": settings,
        "data": settings,
    }


@app.get("/photon/config")
@app.get("/api/photon/config")
def photon_config():
    settings = photon_data()

    return {
        "ok": True,
        "result": "success",
        "photon": settings,
        **settings,
    }


@app.post("/auth/login")
@app.post("/api/auth/login")
@app.post("/api/v1/auth/login")
@app.post("/login")
@app.post("/api/login")
@app.post("/api/v1/login")
@app.post("/user/login")
@app.post("/api/user/login")
@app.post("/api/v1/user/login")
def login(body: FlexibleBody):
    requested_id = body.userId or body.playerId
    user = USERS.get(requested_id or "")

    if user is None:
        user = create_user(body.username or "")

    access_token = secrets.token_urlsafe(32)
    TOKENS[access_token] = user["id"]

    player = player_data(user)

    return {
        "ok": True,
        "success": True,
        "authenticated": True,
        "result": "success",
        "token": access_token,
        "accessToken": access_token,
        "access_token": access_token,
        "sessionToken": access_token,
        "session_token": access_token,
        "expiresIn": 2592000,
        "userId": user["id"],
        "playerId": user["id"],
        "stumbleId": user["id"],
        "user": player,
        "player": player,
        "profile": player,
        "photon": photon_data(),
        "photonJwt": access_token,
        "data": {
            "token": access_token,
            "accessToken": access_token,
            "user": player,
            "player": player,
            "profile": player,
            "photon": photon_data(),
            "photonJwt": access_token,
        },
    }


@app.get("/profile")
@app.get("/me")
@app.get("/api/profile")
@app.get("/api/me")
@app.get("/api/v1/profile")
@app.get("/api/v1/me")
def profile(
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None),
    accessToken: Optional[str] = None,
    token: Optional[str] = None,
):
    user = require_user(
        authorization,
        x_auth_token,
        accessToken,
        token,
    )

    player = player_data(user)

    return {
        "ok": True,
        "result": "success",
        "user": player,
        "player": player,
        "profile": player,
    }


@app.get("/inventory")
@app.get("/api/inventory")
@app.get("/api/v1/inventory")
def inventory(
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None),
    accessToken: Optional[str] = None,
    token: Optional[str] = None,
):
    user = require_user(
        authorization,
        x_auth_token,
        accessToken,
        token,
    )

    return {
        "ok": True,
        "result": "success",
        "userId": user["id"],
        "items": [],
        "skins": [],
        "emotes": [],
        "selectedSkin": user["inventory"].get("skin"),
        "inventory": user["inventory"],
    }


@app.post("/user/inventory/selection")
@app.post("/api/user/inventory/selection")
@app.post("/api/v1/user/inventory/selection")
def inventory_selection(
    body: FlexibleBody,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None),
    accessToken: Optional[str] = None,
    token: Optional[str] = None,
):
    user = get_user_from_token(
        token_from_request(
            authorization,
            x_auth_token,
            accessToken,
            token,
        )
    )

    if user is None:
        user = USERS.get(body.userId or body.playerId or "")

    if user is None:
        user = create_user(body.username or "")

    selection = dict(body.selection)

    for key in ("category", "Category"):
        if key in body.model_extra:
            selection[key] = body.model_extra[key]

    for key in ("itemId", "ItemId"):
        if key in body.model_extra:
            selection[key] = body.model_extra[key]

    user["inventory"].update(selection)

    return {
        "ok": True,
        "success": True,
        "result": "success",
        "userId": user["id"],
        "playerId": user["id"],
        "selected": True,
        "selection": selection,
        "inventory": user["inventory"],
        "data": {
            "inventory": user["inventory"],
            "photon": photon_data(),
        },
    }


@app.get("/shared/{version}/{key}")
@app.get("/api/shared/{version}/{key}")
@app.get("/api/v1/shared/{version}/{key}")
def shared_config(version: int, key: str):
    return {
        "ok": True,
        "result": "success",
        "version": version,
        "key": key,
        "data": {
            "version": GAME_VERSION,
            "maintenance": False,
            "photon": photon_data(),
            "matchmaking": {
                "enabled": True,
                "region": DEFAULT_REGION,
            },
        },
    }


@app.get("/regions")
@app.get("/api/regions")
@app.get("/api/v1/regions")
def regions():
    return {
        "ok": True,
        "result": "success",
        "defaultRegion": DEFAULT_REGION,
        "bestRegion": True,
        "regions": [
            {
                "id": region,
                "code": region,
                "name": region,
                "online": True,
                "players": 0,
            }
            for region in PHOTON_REGIONS
        ],
        "photon": photon_data(),
    }


@app.get("/tournaments")
@app.get("/api/tournaments")
@app.get("/api/v1/tournaments")
def tournaments():
    return {
        "ok": True,
        "result": "success",
        "tournaments": [
            {
                "id": "lend_bd_1v1",
                "name": TOURNAMENTS[0],
                "mode": "1v1",
                "enabled": True,
            },
            {
                "id": "lend_ld_1v1",
                "name": TOURNAMENTS[1],
                "mode": "1v1",
                "enabled": True,
            },
        ],
    }


@app.get("/matchmaking/filter")
@app.get("/api/matchmaking/filter")
@app.get("/api/v1/matchmaking/filter")
def matchmaking_filter():
    return {
        "ok": True,
        "result": "success",
        "enabled": True,
        "region": DEFAULT_REGION,
        "poolId": "default",
        "matchmakingPoolId": "default",
        "filter": {},
        "matchmakingFilter": {},
        "photon": photon_data(),
    }


@app.post("/matchmaking/join")
@app.post("/api/matchmaking/join")
@app.post("/api/v1/matchmaking/join")
@app.post("/matchmaking")
def matchmaking_join(
    body: FlexibleBody,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None),
    accessToken: Optional[str] = None,
    token: Optional[str] = None,
):
    user = require_user(
        authorization,
        x_auth_token,
        accessToken,
        token,
    )

    match_id = str(uuid.uuid4())

    match = {
        "id": match_id,
        "matchId": match_id,
        "status": "waiting",
        "mode": body.model_extra.get("mode", "classic"),
        "region": body.model_extra.get("region", DEFAULT_REGION),
        "players": [
            {
                "id": user["id"],
                "username": user["username"],
            }
        ],
        "createdAt": now(),
    }

    MATCHES[match_id] = match

    return {
        "ok": True,
        "success": True,
        "result": "success",
        "match": match,
        "room": match,
        "photon": photon_data(),
    }


@app.get("/debug/requests")
def debug_requests():
    return {
        "ok": True,
        "requests": REQUEST_LOG,
    }


@app.get("/playername")
@app.get("/api/playername")
@app.get("/api/v1/playername")
def playername():
    number = secrets.randbelow(900000) + 100000
    value = f".gg/sglend{number}"

    return {
        "ok": True,
        "playerName": value,
        "playername": value,
        "serverNumber": str(number),
    }


@app.post("/logout")
@app.post("/api/logout")
def logout(
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None),
    accessToken: Optional[str] = None,
    token: Optional[str] = None,
):
    current = token_from_request(
        authorization,
        x_auth_token,
        accessToken,
        token,
    )

    if current:
        TOKENS.pop(current, None)

    return {
        "ok": True,
        "success": True,
    }






















    




