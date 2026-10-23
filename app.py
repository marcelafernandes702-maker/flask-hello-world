import os
import secrets
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

GAME_INFO = {
    "version": "0.50 to 0.70",
    "bot_name": "Player<sup>zPedrox</sup>",
    "tournament_name": "zPedrox Dev Tbest",
}

API_VERSION = "0.50-0.70"
SERVER_STATUS = "online"

PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Lobby</title>
  <style>
    :root { color-scheme: dark; font-family: Arial, Helvetica, sans-serif; }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; color: #fff; overflow: hidden;
      background: radial-gradient(circle at 50% 20%, #116fa0, transparent 42%),
                  linear-gradient(145deg, #06142c, #0b3c65 58%, #12a6bb); }
    .page { min-height: 100vh; display: grid; place-items: center; padding: 22px; }
    .panel { width: min(620px, 94vw); padding: 34px 26px; text-align: center;
      border: 1px solid rgba(170,240,255,.35); border-radius: 26px;
      background: rgba(3, 18, 43, .78); box-shadow: 0 22px 70px rgba(0,0,0,.4); }
    .logo { width: 84px; height: 84px; margin: 0 auto 18px; display: grid; place-items: center;
      border-radius: 23px; background: #18d0e7; color: #06223c; font-size: 34px;
      font-weight: 900; transform: rotate(-5deg); box-shadow: 0 7px 0 #087d9f; }
    h1 { margin: 0; font-size: clamp(29px, 7vw, 47px); }
    .range { margin-top: 8px; color: #b9f5ff; font-weight: 800; }
    .loading { margin: 30px 0 24px; padding: 22px 18px; border-radius: 17px;
      background: rgba(0,0,0,.25); }
    .loading h2 { margin: 0; font-size: 23px; }
    .loading p { margin: 9px 0 0; color: #d4f8ff; }
    .bar { height: 12px; margin-top: 20px; overflow: hidden; border-radius: 99px;
      background: rgba(255,255,255,.16); }
    .bar::after { content: ""; display: block; width: 38%; height: 100%;
      border-radius: inherit; background: #35ecff; animation: load 1.35s ease-in-out infinite; }
    @keyframes load { from { transform: translateX(-140%); } to { transform: translateX(300%); } }
    .lobby { display: none; }
    body.ready .loading { display: none; }
    body.ready .lobby { display: block; }
    .row { margin: 10px 0; padding: 13px 15px; border-radius: 12px;
      background: rgba(255,255,255,.08); color: #d7f7ff; }
    .row strong { color: #fff; }
    .enter { display: inline-block; margin-top: 18px; padding: 12px 28px; border-radius: 12px;
      background: #24d6eb; color: #06213b; font-weight: 900; text-decoration: none; }
    footer { margin-top: 24px; color: #9ec9d8; font-size: 13px; }
  </style>
</head>
<body>
  <div class="page"><main class="panel">
    <div class="logo">LB</div>
    <h1>Lobby</h1>
    <div class="range">Versions {{ info.version }}</div>

    <section class="loading" aria-live="polite">
      <h2>Transfer elements</h2>
      <p>Transferring elements to enter the lobby...</p>
      <div class="bar" aria-label="Loading"></div>
    </section>

    <section class="lobby" aria-label="Lobby">
      <h2>Elements transferred</h2>
      <div class="row">Bot name: <strong>{{ info.bot_name|safe }}</strong></div>
      <div class="row">Tournaments Name: <strong>{{ info.tournament_name }}</strong></div>
      <a class="enter" href="/lobby">Enter Lobby</a>
    </section>
    <footer>Connection established</footer>
  </main></div>
  <script>setTimeout(() => document.body.classList.add('ready'), 2400);</script>
</body>
</html>"""


@app.get("/")
def home():
    return render_template_string(PAGE, info=GAME_INFO)


@app.get("/lobby")
def lobby():
    return render_template_string(PAGE, info=GAME_INFO)


@app.get("/api/game-info")
def game_info():
    return jsonify(GAME_INFO)


@app.route("/api/user/login", methods=["GET", "POST"])
def user_login():
    payload = request.get_json(silent=True) or {}
    username = payload.get("username") or payload.get("userName") or "Guest"
    return jsonify({
        "success": True,
        "authenticated": True,
        "token": secrets.token_urlsafe(24),
        "user": {"id": username, "username": username},
        "server": "online",
    })


@app.get("/api/info")
def api_info():
    return jsonify({
        "name": "Lobby",
        "versions": GAME_INFO["version"],
        "botName": "PlayerzPedrox",
        "tournamentsName": GAME_INFO["tournament_name"],
        "apiVersion": API_VERSION,
    })


@app.get("/api/config")
def api_config():
    return jsonify({
        "success": True,
        "maintenance": False,
        "registrationEnabled": True,
        "loginEnabled": True,
        "supportedVersions": [f"0.{minor}" for minor in range(50, 71)],
    })


@app.get("/api/version")
def api_version():
    return jsonify({
        "version": API_VERSION,
        "minVersion": "0.50",
        "maxVersion": "0.70",
        "latestVersion": "0.70",
        "updateRequired": False,
    })


@app.get("/api/status")
def api_status():
    return jsonify({
        "status": SERVER_STATUS,
        "online": True,
        "service": "lobby",
        "api": "online",
    })


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "lobby"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)













    




