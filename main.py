import os
import time
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

VERSION = "0.56"
DEFAULT_PLAYER_ID = "1923"
DEFAULT_NICKNAME = ".gg/sgshade"

players = {}
joined_players = {}


def superscript(value: str) -> str:
    table = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
    return str(value).translate(table)


def player_payload(player_id=DEFAULT_PLAYER_ID, nickname=DEFAULT_NICKNAME):
    player_id = str(player_id)

    return {
        "playerId": player_id,
        "nickname": nickname,
        "nicknameSuffix": player_id,
        "displayName": f"{nickname}{superscript(player_id)}",
        "level": 1,
        "isBot": False,
    }


def tournament_template(tournament_id):
    if tournament_id == "1v1_bd":
        name = "Shade BD 1v1"
        card_title = "1v1 BD"
        game_map = "Block Dash"
        description = "Venha jogar stumble shade: https://discord.gg/sgshade"
        amount = 0
    else:
        name = "Shade 1v1 LASER"
        card_title = "1v1 LASER"
        game_map = "Laser Tracer"
        description = "Venha jogar Stumble Shade: https://discord.gg/sgshade"
        amount = 50

    current = len(joined_players.get(tournament_id, {}))

    return {
        "id": tournament_id,
        "name": name,
        "map": game_map,
        "rounds": 1,
        "players": {
            "current": current,
            "max": 2
        },
        "entry": {
            "currency": "gems",
            "amount": amount
        },
        "status": "open",
        "expiresIn": "364d 18h 45m",
        "card": {
            "label": "Torneios",
            "badge": "+1",
            "time": "Tempo restante: 364d 18h 45m",
            "title": card_title,
            "image": game_map
        },
        "details": {
            "title": name,
            "description": description,
            "players": f"{current}/2",
            "rounds": 1,
            "emotes": "Padrão",
            "type": "Padrão",
            "maps": [
                {
                    "round": "Ronda 1",
                    "name": game_map
                }
            ],
            "prizes": [
                "1º",
                "2º a 8º",
                "9º a 16º"
            ],
            "button": "PARTICIPAR",
            "entryButton": str(amount)
        }
    }


def all_tournaments():
    return [
        tournament_template("1v1_bd"),
        tournament_template("1v1_laser")
    ]


def find_player():
    data = request.get_json(silent=True) or {}

    player_id = str(
        data.get("playerId")
        or request.headers.get("X-User-Id")
        or request.headers.get("X-Device-Id")
        or DEFAULT_PLAYER_ID
    )

    nickname = (
        data.get("nickname")
        or request.headers.get("X-Nickname")
        or DEFAULT_NICKNAME
    )

    player = player_payload(player_id, nickname)
    players[player_id] = player

    return player


@app.get("/")
def root():
    return jsonify({
        "name": "Stumble Shade Backend",
        "version": VERSION,
        "status": "ok"
    })


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "stumble-shade",
        "version": VERSION
    })


@app.get("/status")
def status():
    return jsonify({
        "status": "online",
        "version": VERSION
    })


@app.get("/version")
def version():
    return jsonify({
        "version": VERSION
    })


@app.get("/configuration")
def configuration():
    return jsonify({
        "success": True,
        "version": VERSION,
        "game": "Stumble Shade",
        "firstLoad": {
            "screen": "loading",
            "showPopupOnce": True,
            "storageKey": "stumble_shade_first_load_v056",
            "flow": [
                {
                    "step": 1,
                    "screen": "loading",
                    "action": "show_popup_once",
                    "title": "Transferir elementos",
                    "button": "OK"
                },
                {
                    "step": 2,
                    "screen": "loading",
                    "action": "download_progress",
                    "text": "Transferindo elementos essenciais... ({0}/100%)",
                    "initialProgress": 0
                },
                {
                    "step": 3,
                    "screen": "loading",
                    "action": "download_complete",
                    "text": "Transferência de elementos essenciais concluída!",
                    "progress": 100
                },
                {
                    "step": 4,
                    "screen": "lobby",
                    "action": "open_lobby"
                }
            ],
            "title": "Transferir elementos",
            "message": (
                "Atualização necessária!\n"
                "Transferir 69,43 MB de dados?\n"
                "(Recomenda-se a ligação por WIFI)"
            ),
            "button": "OK",
            "progressText": "Transferindo elementos essenciais... ({0}/100%)",
            "completeText": "Transferência de elementos essenciais concluída!"
        },
        "lobby": {
            "tournamentCard": {
                "visibleName": "Card do torneio",
                "internalName": "PLAY_VIEW_TournamentXButton",
                "label": "Torneios",
                "badge": "+1",
                "time": "Tempo restante: 364d 18h 45m",
                "title": "1v1 BD",
                "image": "Block Dash"
            }
        }
    })


@app.get("/api/0.56/first-load")
def first_load():
    """Retorna a sequência visual da primeira entrada no jogo."""
    return configuration()


@app.post("/api/login")
@app.post("/api/auth/login")
@app.post("/login")
@app.post("/user/login")
def login():
    player = find_player()

    return jsonify({
        "success": True,
        "version": VERSION,
        "player": player,
        "accessToken": f"local-{player['playerId']}",
        "refreshToken": f"refresh-{player['playerId']}",
        "status": "ready"
    })


@app.post("/user/refresh")
def user_refresh():
    player = next(
        iter(players.values()),
        player_payload()
    )

    return jsonify({
        "success": True,
        "version": VERSION,
        "player": player,
        "accessToken": f"local-{player['playerId']}",
        "refreshToken": f"refresh-{player['playerId']}",
        "status": "ready"
    })


@app.get("/user/profile")
def user_profile():
    player = next(
        iter(players.values()),
        player_payload()
    )

    return jsonify({
        "success": True,
        "version": VERSION,
        "player": player,
        "profile": player
    })


@app.post("/pusher/authenticate")
def pusher_authenticate():
    data = request.get_json(silent=True) or {}

    socket_id = str(
        data.get("socket_id")
        or request.form.get("socket_id")
        or ""
    )

    channel_name = str(
        data.get("channel_name")
        or request.form.get("channel_name")
        or ""
    )

    return jsonify({
        "auth": f"local-auth:{socket_id}:{channel_name}",
        "channel_data": "{\"user_id\":\"1923\"}"
    })


@app.get("/me")
def me():
    player = next(
        iter(players.values()),
        player_payload()
    )

    return jsonify(player)


@app.get("/me/<path:subpath>")
def me_subpath(subpath):
    player = next(
        iter(players.values()),
        player_payload()
    )

    if subpath == "permissions":
        return jsonify({
            "permissions": []
        })

    if subpath == "rewards":
        return jsonify({
            "rewards": []
        })

    if subpath.startswith("milestones"):
        return jsonify({
            "milestones": []
        })

    return jsonify(player)


@app.get("/api/player")
@app.get("/api/profile")
def api_player():
    return jsonify({
        "success": True,
        "player": next(
            iter(players.values()),
            player_payload()
        )
    })


@app.get("/api/lobby")
@app.get("/api/0.56/lobby")
def lobby():
    return jsonify({
        "success": True,
        "version": VERSION,
        "player": next(
            iter(players.values()),
            player_payload()
        ),
        "wallet": {
            "gems": 6700,
            "tokens": 2000
        },
        "tournamentCard": tournament_template("1v1_bd")["card"],
        "status": "ready"
    })


@app.get("/onlinecheck")
def onlinecheck():
    return jsonify({
        "online": True,
        "status": "ready",
        "version": VERSION
    })


@app.get("/news/getall")
def news():
    return jsonify({
        "news": []
    })


@app.get("/game-events/me")
def game_events_me():
    return jsonify({
        "events": []
    })


@app.get("/friends")
def friends():
    return jsonify({
        "friends": []
    })


@app.get("/party")
def party():
    return jsonify({
        "party": None,
        "members": []
    })


@app.post("/party/invite")
def party_invite():
    data = request.get_json(silent=True) or {}

    return jsonify({
        "success": True,
        "invited": data.get("playerId") or data.get("nickname")
    })


@app.post("/party/cancel")
def party_cancel():
    return jsonify({
        "success": True,
        "cancelled": True
    })


@app.get("/api/0.56/tournaments")
@app.get("/api/tournaments")
@app.get("/tournaments")
def tournaments():
    return jsonify({
        "version": VERSION,
        "tournaments": all_tournaments()
    })


@app.get("/api/0.56/tournaments/<tournament_id>")
def tournament_details(tournament_id):
    if tournament_id not in {"1v1_bd", "1v1_laser"}:
        return jsonify({
            "success": False,
            "message": "Torneio não encontrado"
        }), 404

    return jsonify(
        tournament_template(tournament_id)
    )


@app.post("/api/0.56/tournaments/<tournament_id>/join")
def tournament_join(tournament_id):
    if tournament_id not in {"1v1_bd", "1v1_laser"}:
        return jsonify({
            "success": False,
            "message": "Torneio não encontrado"
        }), 404

    player = find_player()
    room = joined_players.setdefault(tournament_id, {})

    if player["playerId"] not in room and len(room) >= 2:
        return jsonify({
            "success": False,
            "message": "Torneio cheio"
        }), 409

    room[player["playerId"]] = {
        "player": player,
        "status": "waiting",
        "joinedAt": int(time.time())
    }

    tournament = tournament_template(tournament_id)

    return jsonify({
        "success": True,
        "tournamentId": tournament_id,
        "player": player,
        "status": "waiting",
        "players": tournament["players"],
        "message": (
            f"À espera de jogadores... "
            f"({tournament['players']['current']}/"
            f"{tournament['players']['max']})"
        )
    })


@app.get("/api/0.56/tournaments/<tournament_id>/status")
def tournament_status(tournament_id):
    if tournament_id not in {"1v1_bd", "1v1_laser"}:
        return jsonify({
            "success": False,
            "message": "Torneio não encontrado"
        }), 404

    tournament = tournament_template(tournament_id)

    state = (
        "in_match"
        if tournament["players"]["current"] >= 2
        else "waiting"
    )

    if state == "in_match":
        message = "A partida vai começar..."
    else:
        message = (
            f"À espera de jogadores... "
            f"({tournament['players']['current']}/"
            f"{tournament['players']['max']})"
        )

    return jsonify({
        "success": True,
        "tournamentId": tournament_id,
        "status": state,
        "players": tournament["players"],
        "message": message
    })


@app.post("/api/0.56/tournaments/<tournament_id>/result")
def tournament_result(tournament_id):
    if tournament_id not in {"1v1_bd", "1v1_laser"}:
        return jsonify({
            "success": False,
            "message": "Torneio não encontrado"
        }), 404

    data = request.get_json(silent=True) or {}

    return jsonify({
        "success": True,
        "tournamentId": tournament_id,
        "status": "finished",
        "player": (
            data.get("player")
            or next(iter(players.values()), player_payload())
        ),
        "position": data.get("position", 1),
        "message": "Resultado recebido"
    })


@app.post("/game-events/join")
def game_events_join():
    return jsonify({
        "success": True,
        "status": "joined"
    })


@app.get("/api/0.56")
def api_056():
    return jsonify({
        "success": True,
        "version": VERSION,
        "service": "Stumble Shade"
    })


@app.get("/docs")
def docs():
    return jsonify({
        "service": "Stumble Shade Backend",
        "version": VERSION,
        "readme": "Veja README.md"
    })


@app.get("/openapi.json")
def openapi():
    return jsonify({
        "openapi": "3.0.0",
        "info": {
            "title": "Stumble Shade 0.56 API",
            "version": VERSION
        }
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))

    app.run(
        host="0.0.0.0",
        port=port
    )


























    




