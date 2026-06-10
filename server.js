const http = require("node:http");
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
const API_FOOTBALL_BASE_URL = "https://v3.football.api-sports.io";
const API_FOOTBALL_KEY = process.env.API_FOOTBALL_KEY || "";
const WORLD_CUP_LEAGUE_ID = "1";
const WORLD_CUP_SEASON = "2026";
const FOOTBALL_CACHE_MS = 15_000;
const SPORTS_NEWS_URL = "https://ok.surf/api/v1/news-section";
const ESPN_WORLD_CUP_NEWS_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/news";
const SPORTS_NEWS_CACHE_MS = 10 * 60_000;
const PREDICT_FUN_BASE_URL = "https://api.predict.fun";
const PREDICT_FUN_API_KEY = process.env.PREDICT_FUN_API_KEY || "";
const PREDICT_FUN_CACHE_MS = 60_000;
const PREDICT_FUN_PAGE_SIZE = 100;
const PREDICT_FUN_MAX_PAGES = 10;
const ROOT = __dirname;
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
let predictionWriteQueue = Promise.resolve();
let footballCache = {
  expiresAt: 0,
  payload: null,
};
let sportsNewsCache = {
  expiresAt: 0,
  payload: null,
};
let predictFunCache = {
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

function safeJsonParse(value, fallback = []) {
  if (Array.isArray(value)) return value;
  if (value && typeof value === "object") return value;
  try {
    return JSON.parse(value || "[]");
  } catch {
    return fallback;
  }
}

function normalizeMarketText(value) {
  return String(value || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function predictFunOutcomePrice(outcome) {
  const bid = Number(outcome?.bestBid?.price);
  const ask = Number(outcome?.bestAsk?.price);
  if (Number.isFinite(bid) && Number.isFinite(ask)) return (bid + ask) / 2;
  if (Number.isFinite(ask)) return ask;
  if (Number.isFinite(bid)) return bid;
  return 0;
}

function predictFunYesPrice(market) {
  const yes = (market.outcomes || []).find((outcome) => normalizeMarketText(outcome.name) === "yes");
  return predictFunOutcomePrice(yes);
}

function normalizePredictFunMarket(market) {
  const yesPrice = predictFunYesPrice(market);
  return {
    categorySlug: market.categorySlug || "",
    id: String(market.id || market.conditionId || market.categorySlug || ""),
    question: market.question || market.title || "",
    title: market.title || market.question || "",
    tradingStatus: market.tradingStatus || market.status || "",
    updatedAt: market.updatedAt || market.createdAt || "",
    url: market.categorySlug ? "https://predict.fun/markets/" + encodeURIComponent(market.categorySlug) : "https://predict.fun/",
    yesPrice,
  };
}

function isLikelyWorldCupPredictMarket(market) {
  const text = normalizeMarketText([
    market.title,
    market.question,
    market.description,
    market.categorySlug,
  ].filter(Boolean).join(" "));
  return text.includes("fifwc") || text.includes("fifa world cup") || text.includes("world cup");
}

async function fetchPredictFunMarkets() {
  if (!PREDICT_FUN_API_KEY) {
    return {
      configured: false,
      markets: [],
      message: "PREDICT_FUN_API_KEY is not configured",
    };
  }

  const markets = [];
  let after = "";
  for (let page = 0; page < PREDICT_FUN_MAX_PAGES; page += 1) {
    const url = new URL("/v1/markets", PREDICT_FUN_BASE_URL);
    url.searchParams.set("status", "OPEN");
    url.searchParams.set("first", String(PREDICT_FUN_PAGE_SIZE));
    if (after) url.searchParams.set("after", after);

    const response = await fetch(url, {
      headers: {
        Accept: "application/json",
        "x-api-key": PREDICT_FUN_API_KEY,
      },
      signal: AbortSignal.timeout(12_000),
    });
    if (!response.ok) throw new Error("Predict.fun " + response.status);
    const payload = await response.json();
    const pageMarkets = Array.isArray(payload.data) ? payload.data : [];
    markets.push(...pageMarkets.filter(isLikelyWorldCupPredictMarket).map(normalizePredictFunMarket));
    if (!payload.cursor || payload.cursor === after) break;
    after = payload.cursor;
  }

  return {
    configured: true,
    markets,
  };
}

async function getPredictFunGroupOdds() {
  if (predictFunCache.payload && predictFunCache.expiresAt > Date.now()) {
    return predictFunCache.payload;
  }
  try {
    const payload = {
      ...(await fetchPredictFunMarkets()),
      pollIntervalMs: PREDICT_FUN_CACHE_MS,
      stale: false,
      updatedAt: new Date().toISOString(),
    };
    predictFunCache = {
      expiresAt: Date.now() + PREDICT_FUN_CACHE_MS,
      payload,
    };
    return payload;
  } catch (error) {
    if (predictFunCache.payload) {
      return {
        ...predictFunCache.payload,
        errors: [error.message || "Predict.fun request failed"],
        stale: true,
        updatedAt: new Date().toISOString(),
      };
    }
    throw error;
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
  const filePath = path.resolve(ROOT, relativePath);

  if (
    !filePath.startsWith(ROOT) ||
    relativePath.startsWith("data/") ||
    relativePath.startsWith("node_modules/")
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
      service: "checkfifa",
      apiFootballConfigured: Boolean(API_FOOTBALL_KEY),
    });
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
        error: "?????????",
        stale: true,
        updatedAt: new Date().toISOString(),
      });
    }
  }

  if (request.method === "GET" && request.url === "/api/predict/group-odds") {
    try {
      return json(response, 200, await getPredictFunGroupOdds());
    } catch (error) {
      console.error("Predict.fun group odds failed:", error);
      return json(response, 502, {
        configured: Boolean(PREDICT_FUN_API_KEY),
        error: error.message || "Predict.fun request failed",
        markets: [],
        pollIntervalMs: PREDICT_FUN_CACHE_MS,
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
