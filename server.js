const http = require("node:http");
const fs = require("node:fs/promises");
const path = require("node:path");
const { Connection, PublicKey } = require("@solana/web3.js");

const PORT = Number(process.env.PORT || 4173);
const HOST = process.env.HOST || "127.0.0.1";
const RPC_URL = process.env.SOLANA_RPC_URL || "https://api.mainnet-beta.solana.com";
const RECIPIENT = new PublicKey(
  process.env.MY_SOLANA_WALLET || "EwAh2VbsbgG2xWsFsDYMjmCUqq48cSkms1HATZDi3Vgq",
).toBase58();
const USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v";
const PREMIUM_PRICE_UNITS = 19_900_000n;
const DEVELOPER_WALLETS = new Set(
  (process.env.DEVELOPER_WALLETS || RECIPIENT)
    .split(",")
    .map((address) => address.trim())
    .filter(Boolean)
    .map((address) => new PublicKey(address).toBase58()),
);
const ROOT = __dirname;
const PAYMENT_FILE = path.join(ROOT, "data", "payments.json");
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

  if (request.method === "POST" && request.url === "/api/payments/confirm-solana") {
    return confirmSolanaPayment(request, response);
  }

  if (request.method === "POST" && request.url === "/api/payments/status-solana") {
    return checkSolanaPaymentStatus(request, response);
  }

  if (request.method !== "GET") {
    return json(response, 405, { error: "Method not allowed" });
  }

  return serveStatic(request, response);
});

server.listen(PORT, HOST, () => {
  console.log(`FIFA 2026 server running at http://${HOST}:${PORT}`);
});
