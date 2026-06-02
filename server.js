const http = require("node:http");
const fs = require("node:fs/promises");
const path = require("node:path");
const { Connection, PublicKey } = require("@solana/web3.js");

if (typeof process.loadEnvFile === "function") {
  try {
    process.loadEnvFile(path.join(__dirname, ".env"));
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
}

const PORT = Number(process.env.PORT || 4173);
const HOST = process.env.HOST || "127.0.0.1";
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
const DEVELOPER_WALLETS = new Set(
  (process.env.DEVELOPER_WALLETS || RECIPIENT)
    .split(",")
    .map((address) => address.trim())
    .filter(Boolean)
    .map((address) => new PublicKey(address).toBase58()),
);
const ROOT = __dirname;
const PAYMENT_FILE = path.join(ROOT, "data", "payments.json");
const PREDICTION_FILE = path.join(ROOT, "data", "predictions.json");
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

let paymentWriteQueue = Promise.resolve();
let predictionWriteQueue = Promise.resolve();
let footballCache = {
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

function summarizePredictions(predictions) {
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
  return { results, total };
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
  return summarizePredictions(await readPredictions());
}

async function handlePredictions(request, response) {
  try {
    if (request.method === "GET") {
      return json(response, 200, summarizePredictions(await readPredictions()));
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
    if (DEVELOPER_WALLETS.has(normalizedWallet)) {
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
    if (DEVELOPER_WALLETS.has(normalizedWallet)) {
      return json(response, 200, {
        success: true,
        developerMode: true,
        message: "Developer access is active",
      });
    }

    const processed = await readPayments();
    const existing = findRecordedPayment(processed, normalizedWallet);
    if (existing) {
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
  const filePath = path.resolve(ROOT, relativePath);

  const blockedDependency = relativePath.startsWith("node_modules/");

  if (!filePath.startsWith(ROOT) || relativePath.startsWith("data/") || blockedDependency) {
    response.writeHead(403);
    response.end("Forbidden");
    return;
  }

  try {
    const body = await fs.readFile(filePath);
    response.writeHead(200, {
      "Content-Type": MIME_TYPES[path.extname(filePath)] || "application/octet-stream",
      "X-Content-Type-Options": "nosniff",
    });
    response.end(body);
  } catch (error) {
    response.writeHead(error.code === "ENOENT" ? 404 : 500);
    response.end(error.code === "ENOENT" ? "Not found" : "Server error");
  }
}

const server = http.createServer(async (request, response) => {
  if (request.method === "GET" && request.url === "/api/health") {
    return json(response, 200, {
      ok: true,
      recipient: RECIPIENT,
      token: "USDC",
      amount: "19.9",
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

  if (request.method === "POST" && request.url === "/api/payments/confirm-solana") {
    return confirmSolanaPayment(request, response);
  }

  if (request.method === "POST" && request.url === "/api/payments/status-solana") {
    return checkSolanaPaymentStatus(request, response);
  }

  if ((request.method === "GET" || request.method === "POST") && request.url === "/api/predictions") {
    return handlePredictions(request, response);
  }

  if (request.method !== "GET") {
    return json(response, 405, { error: "Method not allowed" });
  }

  return serveStatic(request, response);
});

server.listen(PORT, HOST, () => {
  console.log(`FIFA 2026 server running at http://${HOST}:${PORT}`);
});
