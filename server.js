const http = require("node:http");
const crypto = require("node:crypto");
const fs = require("node:fs/promises");
const path = require("node:path");

if (typeof process.loadEnvFile === "function") {
  try {
    process.loadEnvFile(path.join(__dirname, ".env"));
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
}

const PORT = Number(process.env.PORT || 4173);
const HOST = process.env.HOST || "0.0.0.0";
const PAYMENT_RECIPIENT = process.env.MY_SOLANA_WALLET || "EwAh2VbsbgG2xWsFsDYMjmCUqq48cSkms1HATZDi3Vgq";
const API_FOOTBALL_BASE_URL = "https://v3.football.api-sports.io";
const API_FOOTBALL_KEY = process.env.API_FOOTBALL_KEY || "";
const WORLD_CUP_LEAGUE_ID = "1";
const WORLD_CUP_SEASON = "2026";
const FOOTBALL_CACHE_MS = 15_000;
const SPORTS_NEWS_URL = "https://ok.surf/api/v1/news-section";
const ESPN_WORLD_CUP_NEWS_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/news";
const SPORTS_NEWS_CACHE_MS = 10 * 60_000;
const AUTH_SESSION_MS = 24 * 60 * 60_000;
const AUTH_COOKIE = "fifa2026_session";
const FRONTEND_ACCESS_COOKIE = "fifa2026_frontend_access";
const AUTH_COOKIE_SECURE = process.env.NODE_ENV === "production" ? "; Secure" : "";
const SESSION_SECRET = process.env.SESSION_SECRET || crypto.randomBytes(32).toString("hex");
const DEVELOPER_WALLETS = new Set(
  (process.env.DEVELOPER_WALLETS || PAYMENT_RECIPIENT)
    .split(",")
    .map((address) => address.trim())
    .filter(Boolean),
);
const ROOT = __dirname;
const PROTECTED_ROOT = path.join(ROOT, "protected-pages");
const DATA_ROOT = process.env.VERCEL ? path.join("/tmp", "fifa2026-data") : path.join(ROOT, "data");
const PREDICTION_FILE = path.join(DATA_ROOT, "predictions.json");
const TEAM_CODES = new Set([
  "ALG", "ARG", "AUS", "AUT", "BEL", "BIH", "BRA", "CAN", "CIV", "COD", "COL", "CPV",
  "CRO", "CUW", "CZE", "ECU", "EGY", "ENG", "ESP", "FRA", "GER", "GHA", "HAI", "IRN",
  "IRQ", "JOR", "JPN", "KOR", "KSA", "MAR", "MEX", "NED", "NOR", "NZL", "PAN", "PAR",
  "POR", "QAT", "RSA", "SCO", "SEN", "SUI", "SWE", "TUN", "TUR", "URU", "USA", "UZB",
]);
const MIME_TYPES = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
};
const PROTECTED_HTML = new Set([
  "groups.html",
  "mvp-history.html",
  "predictions.html",
  "semifinals.html",
  "team.html",
]);

let predictionWriteQueue = Promise.resolve();
let footballCache = {
  expiresAt: 0,
  payload: null,
};
let sportsNewsCache = {
  expiresAt: 0,
  payload: null,
};

function json(response, status, payload) {
  response.writeHead(status, {
    "Cache-Control": "no-store",
    "Content-Type": "application/json; charset=utf-8",
  });
  response.end(JSON.stringify(payload));
}

function base64Url(value) {
  return Buffer.from(value).toString("base64url");
}

function signedSession(walletAddress, mode) {
  const payload = base64Url(JSON.stringify({
    expiresAt: Date.now() + AUTH_SESSION_MS,
    mode,
    walletAddress,
  }));
  const signature = crypto.createHmac("sha256", SESSION_SECRET).update(payload).digest("base64url");
  return `${payload}.${signature}`;
}

function parseCookies(request) {
  return Object.fromEntries((request.headers.cookie || "")
    .split(";")
    .map((cookie) => cookie.trim().split("="))
    .filter(([name]) => name));
}

function sessionFromRequest(request) {
  try {
    const token = parseCookies(request)[AUTH_COOKIE];
    if (!token) return null;
    const [payload, signature] = token.split(".");
    const expected = crypto.createHmac("sha256", SESSION_SECRET).update(payload).digest("base64url");
    if (!signature || !crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expected))) return null;
    const session = JSON.parse(Buffer.from(payload, "base64url").toString("utf8"));
    return session.expiresAt > Date.now() ? session : null;
  } catch {
    return null;
  }
}

function setSessionCookie(response, walletAddress, mode) {
  response.setHeader("Set-Cookie", `${AUTH_COOKIE}=${signedSession(walletAddress, mode)}; HttpOnly; Path=/; SameSite=Strict; Max-Age=${AUTH_SESSION_MS / 1000}${AUTH_COOKIE_SECURE}`);
}

function clearSessionCookie(response) {
  response.setHeader("Set-Cookie", `${AUTH_COOKIE}=; HttpOnly; Path=/; SameSite=Strict; Max-Age=0${AUTH_COOKIE_SECURE}`);
}

function isAuthorizedSession(session) {
  return session?.mode === "developer" || session?.mode === "premium";
}

function hasFrontendAccessCookie(request) {
  return Boolean(parseCookies(request)[FRONTEND_ACCESS_COOKIE]);
}

function isAuthorizedRequest(request) {
  return true;
}

async function readJsonBody(request) {
  let body = "";
  for await (const chunk of request) {
    body += chunk;
    if (body.length > 20_000) throw new Error("Request body is too large");
  }
  return JSON.parse(body || "{}");
}

async function fetchFootball(pathname, params = {}) {
  const url = new URL(pathname, API_FOOTBALL_BASE_URL);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") url.searchParams.set(key, value);
  });

  const response = await fetch(url, {
    headers: {
      "x-apisports-key": API_FOOTBALL_KEY,
    },
  });

  if (!response.ok) {
    throw new Error(`API-Football ${response.status}`);
  }

  const payload = await response.json();
  const apiErrors = payload.errors && Object.keys(payload.errors);
  if (apiErrors?.length) {
    throw new Error(`API-Football: ${apiErrors.map((key) => payload.errors[key]).join(", ")}`);
  }
  return payload.response || [];
}

function safeExternalUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:" ? url.toString() : "";
  } catch {
    return "";
  }
}

function formatSportsNewsArticle(article) {
  return {
    imageUrl: safeExternalUrl(article.og || article.image || article.imageUrl || ""),
    link: safeExternalUrl(article.link || article.url || ""),
    publishedAt: article.publishedAt || article.published_at || article.date || "",
    source: article.source || article.publisher || "Sports News",
    title: article.title || "Sports update",
  };
}

async function fetchSportsNews() {
  let espnError;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const response = await fetch(ESPN_WORLD_CUP_NEWS_URL, {
        headers: { Accept: "application/json" },
        signal: AbortSignal.timeout(12_000),
      });
      if (!response.ok) throw new Error(`ESPN ${response.status}`);
      const payload = await response.json();
      const articles = (payload.articles || [])
        .map((article) => formatSportsNewsArticle({
          imageUrl: article.images?.[0]?.url,
          link: article.links?.web?.href,
          publishedAt: article.published,
          source: "ESPN World Cup",
          title: article.headline,
        }))
        .filter((article) => article.link && article.title)
        .slice(0, 60);
      if (!articles.length) throw new Error("ESPN returned no World Cup articles");
      return articles;
    } catch (error) {
      espnError = error;
      if (attempt === 0) await new Promise((resolve) => setTimeout(resolve, 350));
    }
  }

  try {
    const response = await fetch(SPORTS_NEWS_URL, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ sections: ["Sports"] }),
      signal: AbortSignal.timeout(3_500),
    });
    if (!response.ok) throw new Error(`OKSURF ${response.status}`);
    const payload = await response.json();
    const articles = (Array.isArray(payload) ? payload : payload.articles || payload.data || [])
      .map(formatSportsNewsArticle)
      .filter((article) => article.link && article.title)
      .slice(0, 60);
    if (!articles.length) throw new Error("OKSURF returned no sports articles");
    return articles;
  } catch (oksurfError) {
    throw new Error(`${espnError.message}; ${oksurfError.message}`);
  }
}

async function getSportsNews(query = "") {
  const cached = sportsNewsCache.payload;
  if (!cached || sportsNewsCache.expiresAt <= Date.now()) {
    try {
      sportsNewsCache = {
        expiresAt: Date.now() + SPORTS_NEWS_CACHE_MS,
        payload: {
          articles: await fetchSportsNews(),
          stale: false,
          updatedAt: new Date().toISOString(),
        },
      };
    } catch (error) {
      if (!cached) throw error;
      sportsNewsCache = {
        expiresAt: Date.now() + SPORTS_NEWS_CACHE_MS,
        payload: { ...cached, stale: true },
      };
    }
  }
  const normalizedQuery = query.trim().toLowerCase();
  const articles = normalizedQuery
    ? sportsNewsCache.payload.articles.filter((article) =>
      `${article.title} ${article.source}`.toLowerCase().includes(normalizedQuery))
    : sportsNewsCache.payload.articles;
  return {
    ...sportsNewsCache.payload,
    articles: (articles.length ? articles : sportsNewsCache.payload.articles).slice(0, 12),
    query: normalizedQuery,
  };
}

function formatLiveFixture(item, events) {
  return {
    fixtureId: item.fixture.id,
    date: item.fixture.date,
    elapsed: item.fixture.status.elapsed,
    status: item.fixture.status.short,
    statusText: item.fixture.status.long,
    venue: item.fixture.venue?.name || "",
    round: item.league.round || "",
    home: {
      id: item.teams.home.id,
      name: item.teams.home.name,
      logo: item.teams.home.logo,
      score: item.goals.home,
    },
    away: {
      id: item.teams.away.id,
      name: item.teams.away.name,
      logo: item.teams.away.logo,
      score: item.goals.away,
    },
    events: events.map((event) => ({
      assist: event.assist?.name || "",
      detail: event.detail || "",
      player: event.player?.name || "",
      team: event.team?.name || "",
      time: event.time?.elapsed,
      type: event.type || "",
    })),
  };
}

function formatStandings(items) {
  return items.flatMap((item) =>
    (item.league?.standings || []).map((group) =>
      group.map((row) => ({
        all: row.all,
        description: row.description || "",
        form: row.form || "",
        goalsDiff: row.goalsDiff,
        group: row.group || "",
        points: row.points,
        rank: row.rank,
        team: row.team,
      })),
    ),
  );
}

async function getLiveFootballData() {
  if (!API_FOOTBALL_KEY) {
    return {
      configured: false,
      events: [],
      liveMatches: [],
      message: "API_FOOTBALL_KEY is not configured",
      pollIntervalMs: FOOTBALL_CACHE_MS,
      standings: [],
      updatedAt: new Date().toISOString(),
      websocket: false,
    };
  }

  if (footballCache.payload && footballCache.expiresAt > Date.now()) {
    return footballCache.payload;
  }

  const [allLiveFixtures, standingsResult] = await Promise.all([
    fetchFootball("/fixtures", { live: "all" }),
    fetchFootball("/standings", {
      league: WORLD_CUP_LEAGUE_ID,
      season: WORLD_CUP_SEASON,
    }).then(
      (standings) => ({ error: "", standings }),
      (error) => ({ error: error.message, standings: [] }),
    ),
  ]);
  const fixtures = allLiveFixtures.filter(
    (fixture) => String(fixture.league?.id) === WORLD_CUP_LEAGUE_ID,
  );

  const eventGroups = await Promise.all(
    fixtures.map((fixture) =>
      fetchFootball("/fixtures/events", { fixture: String(fixture.fixture.id) }),
    ),
  );

  const liveMatches = fixtures.map((fixture, index) =>
    formatLiveFixture(fixture, eventGroups[index]),
  );
  const payload = {
    configured: true,
    events: liveMatches.flatMap((match) =>
      match.events.map((event) => ({ ...event, fixtureId: match.fixtureId })),
    ),
    liveMatches,
    message: liveMatches.length ? "" : "目前没有正在进行的世界杯比赛",
    pollIntervalMs: FOOTBALL_CACHE_MS,
    standings: formatStandings(standingsResult.standings),
    standingsError: standingsResult.error,
    updatedAt: new Date().toISOString(),
    websocket: false,
  };

  footballCache = {
    expiresAt: Date.now() + FOOTBALL_CACHE_MS,
    payload,
  };
  return payload;
}

function getAuthSession(request, response) {
  const session = sessionFromRequest(request);
  return json(response, 200, {
    authenticated: Boolean(session),
    authorized: isAuthorizedSession(session),
    mode: session?.mode || "",
    walletAddress: session?.walletAddress || "",
  });
}

function logoutWallet(response) {
  clearSessionCookie(response);
  return json(response, 200, { success: true });
}

async function readPredictions() {
  try {
    return JSON.parse(await fs.readFile(PREDICTION_FILE, "utf8"));
  } catch (error) {
    if (error.code === "ENOENT") return [];
    throw error;
  }
}

function summarizePredictions(predictions, voterId = "") {
  const counts = new Map();
  predictions.forEach(({ teamCode }) => {
    counts.set(teamCode, (counts.get(teamCode) || 0) + 1);
  });
  const total = predictions.length;
  const results = [...counts.entries()]
    .map(([teamCode, votes]) => ({
      percentage: total ? (votes / total) * 100 : 0,
      teamCode,
      votes,
    }))
    .sort((a, b) => b.votes - a.votes || a.teamCode.localeCompare(b.teamCode));
  return {
    currentTeamCode: predictions.find((item) => item.voterId === voterId)?.teamCode || "",
    results,
    total,
  };
}

async function savePrediction(voterId, teamCode) {
  predictionWriteQueue = predictionWriteQueue.then(async () => {
    const predictions = await readPredictions();
    const existing = predictions.find((item) => item.voterId === voterId);
    if (existing) {
      existing.teamCode = teamCode;
      existing.updatedAt = new Date().toISOString();
    } else {
      predictions.push({
        teamCode,
        updatedAt: new Date().toISOString(),
        voterId,
      });
    }
    await fs.mkdir(path.dirname(PREDICTION_FILE), { recursive: true });
    await fs.writeFile(PREDICTION_FILE, `${JSON.stringify(predictions, null, 2)}\n`, "utf8");
  });
  await predictionWriteQueue;
  return summarizePredictions(await readPredictions(), voterId);
}

async function handlePredictions(request, response) {
  try {
    const url = new URL(request.url, `http://${request.headers.host || "localhost"}`);
    if (request.method === "GET") {
      return json(response, 200, summarizePredictions(await readPredictions(), url.searchParams.get("voterId") || ""));
    }

    const { teamCode, voterId } = await readJsonBody(request);
    if (!TEAM_CODES.has(teamCode) || !/^[a-zA-Z0-9-]{12,80}$/.test(voterId || "")) {
      return json(response, 400, { error: "Invalid prediction payload" });
    }

    return json(response, 200, await savePrediction(voterId, teamCode));
  } catch (error) {
    console.error("Prediction request failed:", error);
    return json(response, 500, { error: "Prediction request failed" });
  }
}

async function serveStatic(request, response) {
  const url = new URL(request.url, `http://${request.headers.host || "localhost"}`);
  const relativePath = decodeURIComponent(url.pathname === "/" ? "index.html" : url.pathname.slice(1));
  const protectedPage = PROTECTED_HTML.has(relativePath);
  const filePath = protectedPage
    ? path.resolve(PROTECTED_ROOT, relativePath)
    : path.resolve(ROOT, relativePath);

  const blockedDependency = relativePath.startsWith("node_modules/");
  const blockedProtectedSource = relativePath.startsWith("protected-pages/");

  if (
    !filePath.startsWith(protectedPage ? PROTECTED_ROOT : ROOT) ||
    relativePath.startsWith("data/") ||
    blockedDependency ||
    blockedProtectedSource
  ) {
    response.writeHead(403);
    response.end("Forbidden");
    return;
  }
  try {
    const body = await fs.readFile(filePath);
    response.writeHead(200, {
      "Cache-Control": "no-cache",
      "Content-Type": MIME_TYPES[path.extname(filePath)] || "application/octet-stream",
      "X-Content-Type-Options": "nosniff",
    });
    response.end(body);
  } catch (error) {
    response.writeHead(error.code === "ENOENT" ? 404 : 500);
    response.end(error.code === "ENOENT" ? "Not found" : "Server error");
  }
}

async function handleRequest(request, response) {
  if (request.method === "GET" && request.url === "/api/health") {
    return json(response, 200, {
      ok: true,
      recipient: PAYMENT_RECIPIENT,
      token: "USDC",
      amount: "19.9",
    });
  }

  if (request.method === "GET" && request.url === "/api/auth/session") {
    return getAuthSession(request, response);
  }

  if (request.method === "POST" && request.url === "/api/auth/logout") {
    return logoutWallet(response);
  }

  if (request.method === "GET" && request.url === "/api/football/live-matches") {
    try {
      return json(response, 200, await getLiveFootballData());
    } catch (error) {
      console.error("API-Football live matches failed:", error);
      return json(response, 502, {
        configured: Boolean(API_FOOTBALL_KEY),
        error: error.message || "API-Football request failed",
        events: [],
        liveMatches: [],
        pollIntervalMs: FOOTBALL_CACHE_MS,
        standings: [],
        updatedAt: new Date().toISOString(),
        websocket: false,
      });
    }
  }

  if (request.method === "GET" && request.url.startsWith("/api/news/sports")) {
    try {
      const url = new URL(request.url, `http://${request.headers.host || "localhost"}`);
      return json(response, 200, await getSportsNews(url.searchParams.get("team") || ""));
    } catch (error) {
      console.error("Sports news failed:", error);
      return json(response, 502, {
        articles: [],
        error: "体育新闻暂时不可用",
        stale: true,
        updatedAt: new Date().toISOString(),
      });
    }
  }

  if ((request.method === "GET" || request.method === "POST") && request.url.startsWith("/api/predictions")) {
    return handlePredictions(request, response);
  }

  if (request.url.startsWith("/api/")) {
    return json(response, 404, { error: "API endpoint not found" });
  }

  if (request.method !== "GET") {
    return json(response, 405, { error: "Method not allowed" });
  }

  return serveStatic(request, response);
}

if (require.main === module) {
  const server = http.createServer(handleRequest);
  server.listen(PORT, HOST, () => {
    console.log(`FIFA 2026 server running at http://${HOST}:${PORT}`);
  });
}

module.exports = {
  handleRequest,
};
