// =====================
// ENV / DEPENDÊNCIAS
// =====================
require("dotenv").config();

const express = require("express");
const path = require("path");

// =====================
// UTILS
// =====================
const Console = require("./ConsoleUtils");
const CryptoUtils = require("./CryptoUtils");
const SharedUtils = require("./SharedUtils");

const {
  BackendUtils,
  UserModel,
  UserController,
  RoundController,
  BattlePassController,
  EconomyController,
  AnalyticsController,
  FriendsController,
  NewsController,
  MissionsController,
  TournamentXController,
  MatchmakingController,
  TournamentController,
  SocialController,
  EventsController,
  authenticate,
  errorControll,
  sendShared,
  OnlineCheck,
  VerifyPhoton,
} = require("./BackendUtils");

// =====================
// APP
// =====================
const app = express();

app.use(express.json());

// =====================
// CONFIGURAÇÃO
// =====================
const TITLE = "Stumble Lend " + (process.env.VERSION || "dev");
const PORT = process.env.PORT || 3000;

// =====================
// ROTAS PÚBLICAS
// =====================
app.get("/api/v1/ping", (req, res) => {
  res.status(200).send("OK");
});

app.post("/photon/auth", VerifyPhoton);
app.get("/onlinecheck", OnlineCheck);

// =====================
// AUTENTICAÇÃO GLOBAL
// =====================
app.use(authenticate);

// =====================
// CONTROLLER LOCAL
// =====================
class CrownController {
  static async updateScore(req, res) {
    try {
      const { deviceid, username } = req.body;

      if (!deviceid || !username) {
        return res.status(400).json({
          error: "Missing fields",
        });
      }

      const user = await UserModel.findByDeviceId(deviceid);

      if (!user) {
        return res.status(404).json({
          error: "User not found",
        });
      }

      const newCrowns = (user.crowns || 0) + 1;

      await UserModel.update(user.stumbleId, {
        crowns: newCrowns,
      });

      res.json({
        success: true,
        crowns: newCrowns,
      });
    } catch (err) {
      console.error(err);

      res.status(500).json({
        error: "Internal server error",
      });
    }
  }

  static async list(req, res) {
    try {
      const {
        country = "",
        start = 0,
        count = 50,
      } = req.query;

      const data = await UserModel.GetHighscore(
        "crowns",
        country,
        Number(start),
        Number(count),
      );

      res.json(data);
    } catch (err) {
      console.error(err);

      res.status(500).json({
        error: "Internal server error",
      });
    }
  }
}

// =====================
// ROTAS
// =====================
app.get(
  "/matchmaking/filter",
  MatchmakingController.getMatchmakingFilter,
);

app.post("/user/login", UserController.login);

app.get("/user/config", sendShared);

app.get(
  "/usersettings",
  UserController.getSettings,
);

app.post(
  "/user/updateusername",
  UserController.updateUsername,
);

app.get(
  "/user/deleteaccount",
  UserController.deleteAccount,
);

app.post(
  "/user/linkplatform",
  UserController.linkPlatform,
);

app.post(
  "/user/unlinkplatform",
  UserController.unlinkPlatform,
);

app.get(
  "/shared/:version/:type",
  sendShared,
);

app.post(
  "/user/profile",
  UserController.getProfile,
);

app.post(
  "/user-equipped-cosmetics/update",
  UserController.updateCosmetics,
);

app.post(
  "/user/cosmetics/addskin",
  UserController.addSkin,
);

app.post(
  "/user/cosmetics/setequipped",
  UserController.setEquippedCosmetic,
);

// =====================
// RODADAS
// =====================
app.get(
  "/round/finish/:round",
  RoundController.finishRound,
);

app.post(
  "/round/finish/v4/:round",
  RoundController.finishRoundV4,
);

app.post(
  "/round/eventfinish/v4/:round",
  RoundController.finishRoundV4,
);

// =====================
// BATTLE PASS
// =====================
app.get(
  "/battlepass",
  BattlePassController.getBattlePass,
);

app.post(
  "/battlepass/claimv3",
  BattlePassController.claimReward,
);

app.post(
  "/battlepass/purchase",
  BattlePassController.purchaseBattlePass,
);

app.post(
  "/battlepass/complete",
  BattlePassController.completeBattlePass,
);

// =====================
// ECONOMIA
// =====================
app.get(
  "/economy/purchase/:item",
  EconomyController.purchase,
);

app.get(
  "/economy/purchasegasha/:itemId/:count",
  EconomyController.purchaseGasha,
);

app.get(
  "/economy/purchaseluckyspin",
  EconomyController.purchaseLuckySpin,
);

app.post(
  "/economy/:currencyType/give/:amount",
  EconomyController.giveCurrency,
);

// =====================
// MISSÕES
// =====================
app.get(
  "/missions",
  MissionsController.getMissions,
);

app.post(
  "/missions/:missionId/rewards/claim/v2",
  MissionsController.claimMissionReward,
);

app.post(
  "/missions/objective/:objectiveId/:milestoneId/rewards/claim/v2",
  MissionsController.claimMilestoneReward,
);

// =====================
// AMIGOS
// =====================
app.post(
  "/friends/request",
  FriendsController.request,
);

app.post(
  "/friends/accept",
  FriendsController.accept,
);

app.post(
  "/friends/request/decline",
  FriendsController.reject,
);

app.post(
  "/friends/cancel",
  FriendsController.cancel,
);

app.get(
  "/friends",
  FriendsController.list,
);

app.get(
  "/friends/request",
  FriendsController.pending,
);

app.delete(
  "/friends/:UserId",
  FriendsController.remove,
);

// =====================
// EVENTOS E NOTÍCIAS
// =====================
app.get(
  "/game-events/me",
  EventsController.getActive,
);

app.get(
  "/news/getall",
  NewsController.GetNews,
);

// =====================
// ANALYTICS E RANKING
// =====================
app.post(
  "/analytics",
  AnalyticsController.analytic,
);

app.post(
  "/update-crown-score",
  CrownController.updateScore,
);

app.get(
  "/highscore/crowns/list",
  CrownController.list,
);

// =====================
// SOCIAL
// =====================
app.get(
  "/social/interactions",
  SocialController.getInteractions,
);

// =====================
// TORNEIOS
// =====================
app.get(
  "/tournamentx/active",
  TournamentXController.getActive.bind(
    TournamentXController,
  ),
);

app.get(
  "/tournamentx/active/v2",
  TournamentXController.getActive.bind(
    TournamentXController,
  ),
);

app.post(
  "/tournamentx/:tournamentId/join/v2",
  TournamentXController.join.bind(
    TournamentXController,
  ),
);

app.post(
  "/tournamentx/:tournamentId/leave",
  TournamentXController.leave.bind(
    TournamentXController,
  ),
);

app.post(
  "/tournamentx/:tournamentId/finish",
  TournamentXController.finish.bind(
    TournamentXController,
  ),
);

app.post(
  "/api/v1/userLoginExternal",
  TournamentController.login,
);

app.get(
  "/api/v1/tournaments",
  TournamentController.getActive,
);

// =====================
// TRATAMENTO DE ERROS
// =====================
app.use(errorControll);

// =====================
// INICIALIZAÇÃO
// =====================
app.listen(PORT, () => {
  const now = new Date()
    .toLocaleString()
    .replace(",", " |");

  console.clear();

  Console.log(
    "Server",
    `[${TITLE}] | ${now} | ${CryptoUtils.SessionToken()}`,
  );

  Console.log(
    "Server",
    `Listening on port ${PORT}`,
  );
});
































    




