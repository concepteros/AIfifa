const http = require("node:http");
const crypto = require("node:crypto");
const fs = require("node:fs/promises");
const path = require("node:path");
const { Connection, PublicKey } = require("@solana/web3.js");
const bs58Module = require("bs58");
const nacl = require("tweetnacl");
const bs58 = bs58Module.default || bs58Module;

if (typeof process.loadEnvFile === "function") {
  try {
    process.loadEnvFile(path.join(__dirname, ".env"));
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
}

const PORT = Number(process.env.PORT || 4173);
const HOST = process.env.HOST || "0.0.0.0";
const RPC_URL = process.env.SOLANA_RPC_URL || "https://api.mainnet-beta.solana.com";
const RECIPIENT = new PublicKey(
  process.env.MY_SOLANA_WALLET || "EwAh2VbsbgG2xWsFsDYMjmCUqq48cSkms1HATZDi3Vgq",
).toBase58();
const USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v";
const PREMIUM_PRICE_UNITS = 19_900_000n;
const API_FOOTBALL_BASE_URL = "https://v3.football.api-sports.io";
const API_FOOTBALL_KEY = process.env.API_FOOTBALL_KEY || "";
const WORLD_CUP_LEAGUE_ID = "1";
const WORLD_CUP_SEASON = "2026";
const FOOTBALL_CACHE_MS = 15_000;
const POLYMARKET_BASE_URL = "https://gamma-api.polymarket.com";
const POLYMARKET_CACHE_MS = 15_000;
const POLYMARKET_DATA_URL = "https://data-api.polymarket.com";
const POLYMARKET_WORLD_CUP_SERIES_ID = "11433";
const POLYMARKET_WORLD_CUP_SPORT = "fifwc";
const SMART_MONEY_CACHE_MS = 5_000;
const SMART_MONEY_RANKING_CACHE_MS = 5 * 60_000;
const SPORTS_NEWS_URL = "https://ok.surf/api/v1/news-section";
const ESPN_WORLD_CUP_NEWS_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/news";
const SPORTS_NEWS_CACHE_MS = 10 * 60_000;
const AUTH_CHALLENGE_MS = 5 * 60_000;
const AUTH_SESSION_MS = 24 * 60 * 60_000;
const AUTH_COOKIE = "fifa2026_session";
const AUTH_COOKIE_SECURE = process.env.NODE_ENV === "production" ? "; Secure" : "";
const SESSION_SECRET = process.env.SESSION_SECRET || crypto.randomBytes(32).toString("hex");
const DEVELOPER_WALLETS = new Set(
  (process.env.DEVELOPER_WALLETS || RECIPIENT)
    .split(",")
    .map((address) => address.trim())
    .filter(Boolean)
    .map((address) => new PublicKey(address).toBase58()),
);
const ROOT = __dirname;
const PROTECTED_ROOT = path.join(ROOT, "protected-pages");
const DATA_ROOT = process.env.VERCEL ? path.join("/tmp", "fifa2026-data") : path.join(ROOT, "data");
const PAYMENT_FILE = path.join(DATA_ROOT, "payments.json");
const PREDICTION_FILE = path.join(DATA_ROOT, "predictions.json");
const TEAM_CODES = new Set([
  "ALG", "ARG", "AUS", "AUT", "BEL", "BIH", "BRA", "CAN", "CIV", "COD", "COL", "CPV",
  "CRO", "CUW", "CZE", "ECU", "EGY", "ENG", "ESP", "FRA", "GER", "GHA", "HAI", "IRN",
  "IRQ", "JOR", "JPN", "KOR", "KSA", "MAR", "MEX", "NED", "NOR", "NZL", "PAN", "PAR",
  "POR", "QAT", "RSA", "SCO", "SEN", "SUI", "SWE", "TUN", "TUR", "URU", "USA", "UZB",
]);
const connection = new Connection(RPC_URL, "confirmed");

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

let paymentWriteQueue = Promise.resolve();
let predictionWriteQueue = Promise.resolve();
let footballCache = {
  expiresAt: 0,
  payload: null,
};
let polymarketGamesCache = {
  expiresAt: 0,
  payload: null,
};
let sportsNewsCache = {
  expiresAt: 0,
  payload: null,
};
let smartMoneyRankingCache = {
  expiresAt: 0,
  wallets: [],
};
let smartMoneyRankingPromise = null;
const smartMoneyFeedCache = new Map();
const smartMoneyFeedPromises = new Map();

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

function signedChallengeToken(challenge) {
  const payload = base64Url(JSON.stringify(challenge));
  const signature = crypto.createHmac("sha256", SESSION_SECRET).update(payload).digest("base64url");
  return `${payload}.${signature}`;
}

function challengeFromToken(token) {
  try {
    const [payload, signature] = String(token || "").split(".");
    if (!payload || !signature) return null;
    const expected = crypto.createHmac("sha256", SESSION_SECRET).update(payload).digest("base64url");
    if (!crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expected))) return null;
    return JSON.parse(Buffer.from(payload, "base64url").toString("utf8"));
  } catch {
    return null;
  }
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

function requireWalletSession(request, response, walletAddress) {
  const session = sessionFromRequest(request);
  if (!session || session.walletAddress !== walletAddress) {
    json(response, 401, { error: "Wallet authentication required" });
    return null;
  }
  return session;
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

function parseMaybeJson(value) {
  if (Array.isArray(value)) return value;
  if (typeof value !== "string") return [];
  try {
    return JSON.parse(value);
  } catch {
    return value.split(",").map((item) => item.trim()).filter(Boolean);
  }
}

function asPercentage(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return null;
  return Math.max(0, Math.min(100, number <= 1 ? number * 100 : number));
}

function isWorldCupGameEvent(event) {
  const text = [
    event.title,
    event.slug,
    ...(event.markets || []).flatMap((market) => [market.question, market.slug, market.groupItemTitle]),
  ].filter(Boolean).join(" ").toLowerCase();
  return (
    (text.includes("world cup") || String(event.slug || "").startsWith("fifwc-")) &&
    (/\bvs\.?\s/.test(text) || text.includes("-vs-")) &&
    !text.includes("women") &&
    !text.includes("u19") &&
    !text.includes("qualifier")
  );
}

function formatPolymarketGame(event) {
  const activeMarkets = (event.markets || [])
    .filter((market) => market && !market.closed && market.active !== false);
  const moneylineMarkets = activeMarkets.filter((market) => market.sportsMarketType === "moneyline");
  const markets = moneylineMarkets.length
    ? [{
      id: `moneyline-${event.id}`,
      liquidity: moneylineMarkets.reduce((total, market) => total + Number(market.liquidityNum || market.liquidity || 0), 0),
      marketType: "moneyline",
      outcomes: moneylineMarkets.map((market) => ({
        label: String(market.groupItemTitle || market.question || "Outcome").replace(/\s+\(.+\)$/, ""),
        percentage: asPercentage(parseMaybeJson(market.outcomePrices)[0]),
      })).filter((outcome) => outcome.percentage !== null),
      question: "胜负线",
      volume: moneylineMarkets.reduce((total, market) => total + Number(market.volumeNum || market.volume || 0), 0),
    }]
    : activeMarkets
      .slice(0, 6)
      .map((market) => {
        const outcomes = parseMaybeJson(market.outcomes);
        const prices = parseMaybeJson(market.outcomePrices);
        return {
          id: market.id,
          liquidity: Number(market.liquidityNum || market.liquidity || 0),
          marketType: market.sportsMarketType || market.marketType || "",
          outcomes: outcomes.map((outcome, index) => ({
            label: String(outcome),
            percentage: asPercentage(prices[index]),
          })).filter((outcome) => outcome.percentage !== null),
          question: market.question || market.groupItemTitle || "Match odds",
          volume: Number(market.volumeNum || market.volume || 0),
        };
      });
  return {
    eventUrl: `https://polymarket.com/zh/sports/world-cup/${event.slug}`,
    id: event.id,
    imageUrl: safeExternalUrl(event.image || event.icon || ""),
    liquidity: Number(event.liquidity || 0),
    live: Boolean(event.live),
    markets,
    startTime: event.startTime || event.endDate || "",
    slug: event.slug || "",
    title: event.title || event.slug,
    volume: Number(event.volume || 0),
  };
}

async function getPolymarketWorldCupGames() {
  if (polymarketGamesCache.payload && polymarketGamesCache.expiresAt > Date.now()) {
    return polymarketGamesCache.payload;
  }

  const sportsUrl = new URL("/sports", POLYMARKET_BASE_URL);
  const eventsUrl = new URL("/events", POLYMARKET_BASE_URL);
  Object.entries({
    active: "true",
    closed: "false",
    limit: "100",
  }).forEach(([key, value]) => eventsUrl.searchParams.set(key, value));

  let lastError;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const sportsResponse = await fetch(sportsUrl, {
        headers: { Accept: "application/json" },
        signal: AbortSignal.timeout(12_000),
      });
      if (!sportsResponse.ok) throw new Error(`Polymarket sports ${sportsResponse.status}`);
      const sports = await sportsResponse.json();
      const worldCup = sports.find((sport) => sport.sport === POLYMARKET_WORLD_CUP_SPORT);
      eventsUrl.searchParams.set("series_id", worldCup?.series || POLYMARKET_WORLD_CUP_SERIES_ID);
      const eventsResponse = await fetch(eventsUrl, {
        headers: { Accept: "application/json" },
        signal: AbortSignal.timeout(12_000),
      });
      if (!eventsResponse.ok) throw new Error(`Polymarket events ${eventsResponse.status}`);
      const games = (await eventsResponse.json())
        .filter(isWorldCupGameEvent)
        .filter((event) => !event.slug.includes("-more-markets"))
        .map(formatPolymarketGame);
      const payload = {
        games,
        message: games.length ? "" : "等待开赛",
        pollIntervalMs: POLYMARKET_CACHE_MS,
        stale: false,
        updatedAt: new Date().toISOString(),
      };
      polymarketGamesCache = {
        expiresAt: Date.now() + POLYMARKET_CACHE_MS,
        payload,
      };
      return payload;
    } catch (error) {
      lastError = error;
      if (attempt === 0) await new Promise((resolve) => setTimeout(resolve, 350));
    }
  }

  if (polymarketGamesCache.payload) {
    return {
      ...polymarketGamesCache.payload,
      stale: true,
    };
  }
  throw lastError;
}

async function fetchPolymarketData(pathname, params = {}) {
  const url = new URL(pathname, POLYMARKET_DATA_URL);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") url.searchParams.set(key, String(value));
  });
  let lastError;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      const response = await fetch(url, { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`Polymarket Data API ${response.status}`);
      return await response.json();
    } catch (error) {
      lastError = error;
      if (attempt < 2) {
        await new Promise((resolve) => setTimeout(resolve, 350 * (attempt + 1)));
      }
    }
  }
  throw lastError;
}

function isWalletAddress(value) {
  return /^0x[a-fA-F0-9]{40}$/.test(value || "");
}

function shortWallet(address) {
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

function isSportsTrade(item) {
  const text = `${item.title || ""} ${item.slug || ""} ${item.eventSlug || ""}`.toLowerCase();
  return (
    /\bvs\b/.test(text) ||
    [
      "soccer", "football", "world cup", "premier league", "champions league", "europa league",
      "la liga", "bundesliga", "serie a", "ligue 1", "mls", "nba", "wnba", "nfl", "nhl",
      "mlb", "ufc", "tennis", "cricket", "fifa", "uefa",
    ].some((keyword) => text.includes(keyword))
  );
}

function isFootballTrade(item) {
  const text = `${item.title || ""} ${item.slug || ""} ${item.eventSlug || ""}`.toLowerCase();
  return [
    "soccer", "football", "world cup", "premier league", "champions league", "europa league",
    "la liga", "bundesliga", "serie a", "ligue 1", "mls", "fifa", "uefa",
  ].some((keyword) => text.includes(keyword));
}

async function estimateSportsWinRate(address) {
  try {
    const positions = await fetchPolymarketData("/closed-positions", {
      limit: 50,
      offset: 0,
      sortBy: "TIMESTAMP",
      sortDirection: "DESC",
      user: address,
    });
    const sports = positions.filter(isSportsTrade);
    const sample = sports.length ? sports : positions;
    if (!sample.length) return { sampleSize: 0, winRate: null };
    const wins = sample.filter((position) => Number(position.realizedPnl) > 0).length;
    return { sampleSize: sample.length, winRate: (wins / sample.length) * 100 };
  } catch {
    return { sampleSize: 0, winRate: null };
  }
}

async function getSmartMoneyRanking() {
  if (smartMoneyRankingCache.wallets.length && smartMoneyRankingCache.expiresAt > Date.now()) {
    return smartMoneyRankingCache.wallets;
  }
  if (smartMoneyRankingPromise) return smartMoneyRankingPromise;
  smartMoneyRankingPromise = (async () => {
    const ranking = await fetchPolymarketData("/v1/leaderboard", {
      category: "SPORTS",
      limit: 25,
      offset: 0,
      orderBy: "PNL",
      timePeriod: "MONTH",
    });
    const winRates = await Promise.all(ranking.map((wallet) => estimateSportsWinRate(wallet.proxyWallet)));
    const wallets = ranking
      .map((wallet, index) => ({
        address: wallet.proxyWallet,
        label: wallet.userName || shortWallet(wallet.proxyWallet),
        pnl: Number(wallet.pnl || 0),
        sampleSize: winRates[index].sampleSize,
        sourceRank: Number(wallet.rank || index + 1),
        volume: Number(wallet.vol || 0),
        winRate: winRates[index].winRate,
      }))
      .sort((left, right) =>
        (right.winRate ?? -1) - (left.winRate ?? -1) || right.pnl - left.pnl,
      )
      .map((wallet, index) => ({ ...wallet, rank: index + 1 }));
    smartMoneyRankingCache = {
      expiresAt: Date.now() + SMART_MONEY_RANKING_CACHE_MS,
      wallets,
    };
    return wallets;
  })();
  try {
    return await smartMoneyRankingPromise;
  } finally {
    smartMoneyRankingPromise = null;
  }
}

function formatSmartMoneyTrade(trade, trackedWallets) {
  const wallet = trackedWallets.get(trade.proxyWallet.toLowerCase());
  return {
    address: trade.proxyWallet,
    amount: Number(trade.size || 0) * Number(trade.price || 0),
    eventUrl: trade.eventSlug ? `https://polymarket.com/event/${trade.eventSlug}` : "",
    football: isFootballTrade(trade),
    label: wallet?.label || trade.name || trade.pseudonym || shortWallet(trade.proxyWallet),
    outcome: trade.outcome || "",
    price: Number(trade.price || 0) * 100,
    side: trade.side || "",
    size: Number(trade.size || 0),
    timestamp: Number(trade.timestamp || 0),
    title: trade.title || trade.slug || "Sports market",
    transactionHash: trade.transactionHash || "",
  };
}

function parseCustomWallets(url) {
  return [...new Set((url.searchParams.get("wallets") || "")
    .split(",")
    .map((wallet) => wallet.trim().toLowerCase())
    .filter(isWalletAddress))]
    .slice(0, 20);
}

async function getSmartMoneyFeed(customWallets = []) {
  const cacheKey = customWallets.join(",");
  const cached = smartMoneyFeedCache.get(cacheKey);
  if (cached && cached.expiresAt > Date.now()) return cached.payload;
  if (smartMoneyFeedPromises.has(cacheKey)) return smartMoneyFeedPromises.get(cacheKey);

  const feedPromise = (async () => {
    try {
    const ranking = await getSmartMoneyRanking();
    const trackedWallets = new Map(ranking.map((wallet) => [wallet.address.toLowerCase(), wallet]));
    customWallets.forEach((address) => {
      if (!trackedWallets.has(address)) {
        trackedWallets.set(address, { address, label: shortWallet(address), custom: true });
      }
    });

    const [recentTrades, ...customTrades] = await Promise.all([
      fetchPolymarketData("/trades", { limit: 1000, offset: 0, takerOnly: false }),
      ...customWallets.map((user) =>
        fetchPolymarketData("/trades", { limit: 40, offset: 0, takerOnly: false, user }).catch(() => []),
      ),
    ]);
    const seen = new Set();
    const trades = [...recentTrades, ...customTrades.flat()]
      .filter((trade) => trade.proxyWallet && trackedWallets.has(trade.proxyWallet.toLowerCase()))
      .filter(isSportsTrade)
      .filter((trade) => {
        const key = `${trade.proxyWallet}:${trade.transactionHash}:${trade.asset}:${trade.side}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      })
      .sort((a, b) => Number(b.timestamp) - Number(a.timestamp))
      .slice(0, 80)
      .map((trade) => formatSmartMoneyTrade(trade, trackedWallets));

    const payload = {
      customWallets,
      pollIntervalMs: SMART_MONEY_CACHE_MS,
      ranking,
      stale: false,
      trades,
      updatedAt: new Date().toISOString(),
    };
    smartMoneyFeedCache.set(cacheKey, {
      expiresAt: Date.now() + SMART_MONEY_CACHE_MS,
      payload,
    });
      return payload;
    } catch (error) {
      if (!cached?.payload) throw error;
      return {
        ...cached.payload,
        stale: true,
      };
    }
  })();
  smartMoneyFeedPromises.set(cacheKey, feedPromise);
  try {
    return await feedPromise;
  } finally {
    smartMoneyFeedPromises.delete(cacheKey);
  }
}

function streamSmartMoney(request, response) {
  const url = new URL(request.url, `http://${request.headers.host || "localhost"}`);
  const customWallets = parseCustomWallets(url);
  response.writeHead(200, {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "Content-Type": "text/event-stream; charset=utf-8",
  });
  const send = async () => {
    try {
      response.write(`data: ${JSON.stringify(await getSmartMoneyFeed(customWallets))}\n\n`);
    } catch (error) {
      response.write(`event: error\ndata: ${JSON.stringify({ error: "聪明钱数据暂时不可用" })}\n\n`);
    }
  };
  send();
  const interval = setInterval(send, SMART_MONEY_CACHE_MS);
  request.on("close", () => clearInterval(interval));
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

async function readPayments() {
  try {
    return JSON.parse(await fs.readFile(PAYMENT_FILE, "utf8"));
  } catch (error) {
    if (error.code === "ENOENT") return [];
    throw error;
  }
}

function walletLoginMessage(walletAddress, nonce) {
  return [
    "FIFA 2026 Wallet Login",
    `Wallet: ${walletAddress}`,
    `Nonce: ${nonce}`,
    "Sign this message to prove wallet ownership. This does not send a transaction.",
  ].join("\n");
}

function decodeWalletSignature(signature) {
  if (typeof signature !== "string") return null;
  try {
    const bytes = Buffer.from(signature, "base64");
    if (bytes.length === nacl.sign.signatureLength) return bytes;
  } catch {}
  try {
    const bytes = Buffer.from(bs58.decode(signature));
    return bytes.length === nacl.sign.signatureLength ? bytes : null;
  } catch {
    return null;
  }
}

async function accessModeForWallet(walletAddress) {
  if (DEVELOPER_WALLETS.has(walletAddress)) return "developer";
  return findRecordedPayment(await readPayments(), walletAddress) ? "premium" : "wallet";
}

async function createWalletChallenge(request, response) {
  try {
    const { walletAddress } = await readJsonBody(request);
    const normalizedWallet = new PublicKey(walletAddress).toBase58();
    const nonce = crypto.randomBytes(18).toString("base64url");
    const challenge = {
      expiresAt: Date.now() + AUTH_CHALLENGE_MS,
      message: walletLoginMessage(normalizedWallet, nonce),
      walletAddress: normalizedWallet,
    };
    return json(response, 200, {
      challengeId: signedChallengeToken(challenge),
      message: challenge.message,
    });
  } catch {
    return json(response, 400, { error: "Invalid wallet address" });
  }
}

async function loginWithWallet(request, response) {
  try {
    const { challengeId, signature, walletAddress } = await readJsonBody(request);
    const normalizedWallet = new PublicKey(walletAddress).toBase58();
    const challenge = challengeFromToken(challengeId);
    const signatureBytes = decodeWalletSignature(signature);
    if (
      !challenge ||
      challenge.expiresAt <= Date.now() ||
      challenge.walletAddress !== normalizedWallet ||
      !signatureBytes ||
      !nacl.sign.detached.verify(
        Buffer.from(challenge.message, "utf8"),
        signatureBytes,
        new PublicKey(normalizedWallet).toBytes(),
      )
    ) {
      return json(response, 401, { error: "Wallet signature verification failed" });
    }
    const mode = await accessModeForWallet(normalizedWallet);
    setSessionCookie(response, normalizedWallet, mode);
    return json(response, 200, {
      authorized: mode !== "wallet",
      developerMode: mode === "developer",
      mode,
      walletAddress: normalizedWallet,
    });
  } catch {
    return json(response, 400, { error: "Invalid wallet login payload" });
  }
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

async function recordPayment(payment) {
  paymentWriteQueue = paymentWriteQueue.then(async () => {
    const payments = await readPayments();
    if (payments.some((item) => item.signature === payment.signature)) {
      throw new Error("Transaction was already processed");
    }
    payments.push(payment);
    await fs.mkdir(path.dirname(PAYMENT_FILE), { recursive: true });
    await fs.writeFile(PAYMENT_FILE, `${JSON.stringify(payments, null, 2)}\n`, "utf8");
  });
  return paymentWriteQueue;
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

function findRecordedPayment(payments, payer) {
  return payments.find((item) => item.payer === payer);
}

function payerFromTransaction(transaction) {
  return transaction.transaction.message.accountKeys
    .find((account) => account.signer)
    ?.pubkey.toBase58();
}

function hasExpectedUsdcTransfer(transaction) {
  return (transaction.meta?.postTokenBalances || []).some((post) => {
    const pre = transaction.meta?.preTokenBalances?.find(
      (item) => item.accountIndex === post.accountIndex,
    );
    const delta =
      BigInt(post.uiTokenAmount.amount) -
      BigInt(pre?.uiTokenAmount.amount || "0");

    return (
      post.mint === USDC_MINT &&
      post.owner === RECIPIENT &&
      delta >= PREMIUM_PRICE_UNITS
    );
  });
}

async function verifyTransaction(signature, expectedWallet) {
  const transaction = await connection.getParsedTransaction(signature, {
    commitment: "finalized",
    maxSupportedTransactionVersion: 0,
  });

  if (!transaction || transaction.meta?.err || !hasExpectedUsdcTransfer(transaction)) {
    return null;
  }

  const payer = payerFromTransaction(transaction);
  if (!payer || payer !== expectedWallet) return null;

  return {
    amount: "19.9",
    confirmedAt: new Date().toISOString(),
    payer,
    recipient: RECIPIENT,
    signature,
    status: "confirmed",
    token: "USDC",
  };
}

async function confirmSolanaPayment(request, response) {
  try {
    const { signature, walletAddress } = await readJsonBody(request);
    if (!signature || !walletAddress) {
      return json(response, 400, { error: "Missing signature or walletAddress" });
    }

    const normalizedWallet = new PublicKey(walletAddress).toBase58();
    if (!requireWalletSession(request, response, normalizedWallet)) return;
    if (DEVELOPER_WALLETS.has(normalizedWallet)) {
      setSessionCookie(response, normalizedWallet, "developer");
      return json(response, 200, {
        success: true,
        developerMode: true,
        message: "Developer access is active",
      });
    }

    const processed = await readPayments();
    if (processed.some((item) => item.signature === signature)) {
      return json(response, 409, { error: "Transaction was already processed" });
    }

    const payment = await verifyTransaction(signature, normalizedWallet);
    if (!payment) {
      return json(response, 400, { error: "Expected finalized 19.9 USDC payment was not found" });
    }

    await recordPayment(payment);
    setSessionCookie(response, normalizedWallet, "premium");

    return json(response, 200, {
      success: true,
      amount: "19.9",
      message: "Payment verified. Permanent access is active.",
    });
  } catch (error) {
    console.error("Solana payment verification failed:", error);
    return json(response, 400, { error: error.message || "Payment verification failed" });
  }
}

async function checkSolanaPaymentStatus(request, response) {
  try {
    const { walletAddress } = await readJsonBody(request);
    if (!walletAddress) {
      return json(response, 400, { error: "Missing walletAddress" });
    }

    const normalizedWallet = new PublicKey(walletAddress).toBase58();
    if (!requireWalletSession(request, response, normalizedWallet)) return;
    if (DEVELOPER_WALLETS.has(normalizedWallet)) {
      setSessionCookie(response, normalizedWallet, "developer");
      return json(response, 200, {
        success: true,
        developerMode: true,
        message: "Developer access is active",
      });
    }

    const processed = await readPayments();
    const existing = findRecordedPayment(processed, normalizedWallet);
    if (existing) {
      setSessionCookie(response, normalizedWallet, "premium");
      return json(response, 200, {
        success: true,
        amount: existing.amount,
        signature: existing.signature,
      });
    }

    const signatures = await connection.getSignaturesForAddress(
      new PublicKey(normalizedWallet),
      { limit: 20 },
      "finalized",
    );

    for (const item of signatures) {
      if (item.err) continue;
      if (processed.some((payment) => payment.signature === item.signature)) continue;

      const payment = await verifyTransaction(item.signature, normalizedWallet);
      if (!payment) continue;

      await recordPayment(payment);
      setSessionCookie(response, normalizedWallet, "premium");
      return json(response, 200, {
        success: true,
        amount: payment.amount,
        signature: payment.signature,
      });
    }

    return json(response, 200, {
      success: false,
      pending: true,
      message: "Payment has not been detected yet",
    });
  } catch (error) {
    console.error("Solana payment status check failed:", error);
    return json(response, 400, { error: error.message || "Payment status check failed" });
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
  if (protectedPage && !isAuthorizedSession(sessionFromRequest(request))) {
    response.writeHead(302, { Location: "/index.html" });
    response.end();
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
      recipient: RECIPIENT,
      token: "USDC",
      amount: "19.9",
    });
  }

  if (request.method === "POST" && request.url === "/api/auth/challenge") {
    return createWalletChallenge(request, response);
  }

  if (request.method === "POST" && request.url === "/api/auth/wallet-login") {
    return loginWithWallet(request, response);
  }

  if (request.method === "GET" && request.url === "/api/auth/session") {
    return getAuthSession(request, response);
  }

  if (request.method === "POST" && request.url === "/api/auth/logout") {
    return logoutWallet(response);
  }

  if (
    request.url.startsWith("/api/") &&
    !request.url.startsWith("/api/payments/") &&
    !isAuthorizedSession(sessionFromRequest(request))
  ) {
    return json(response, 401, { error: "Premium wallet session required" });
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

  if (request.method === "GET" && request.url === "/api/polymarket/world-cup-games") {
    try {
      return json(response, 200, await getPolymarketWorldCupGames());
    } catch (error) {
      console.error("Polymarket World Cup games failed:", error);
      return json(response, 502, {
        error: "盘口数据暂时不可用",
        games: [],
        message: "等待开赛",
        pollIntervalMs: POLYMARKET_CACHE_MS,
        updatedAt: new Date().toISOString(),
      });
    }
  }

  if (request.method === "GET" && request.url.startsWith("/api/polymarket/smart-money-stream")) {
    return streamSmartMoney(request, response);
  }

  if (request.method === "GET" && request.url.startsWith("/api/polymarket/smart-money")) {
    try {
      const url = new URL(request.url, `http://${request.headers.host || "localhost"}`);
      return json(response, 200, await getSmartMoneyFeed(parseCustomWallets(url)));
    } catch (error) {
      console.error("Polymarket smart money failed:", error);
      return json(response, 502, { error: "聪明钱数据暂时不可用" });
    }
  }

  if (request.method === "POST" && request.url === "/api/payments/confirm-solana") {
    return confirmSolanaPayment(request, response);
  }

  if (request.method === "POST" && request.url === "/api/payments/status-solana") {
    return checkSolanaPaymentStatus(request, response);
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
