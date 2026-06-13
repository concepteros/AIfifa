import test from "node:test";
import assert from "node:assert/strict";

import { createServer } from "../src/server.js";

async function startTestServer() {
  const server = createServer();
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address();
  const baseUrl = `http://127.0.0.1:${port}`;
  return {
    baseUrl,
    close: () => new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()))
  };
}

test("GET /health returns service health", async () => {
  const server = await startTestServer();
  try {
    const response = await fetch(`${server.baseUrl}/health`);
    const payload = await response.json();

    assert.equal(response.status, 200);
    assert.deepEqual(payload, {
      ok: true,
      service: "prediction-copytrader-executor"
    });
  } finally {
    await server.close();
  }
});

test("GET /api/status returns conservative status", async () => {
  const server = await startTestServer();
  try {
    const response = await fetch(`${server.baseUrl}/api/status`);
    const payload = await response.json();

    assert.equal(response.status, 200);
    assert.equal(payload.wallet.vault, "missing");
    assert.equal(payload.risk.emergencyPaused, false);
    assert.equal(payload.risk.maxOrderUsd, 10);
    assert.equal(payload.panels.strategy.observing, 1);
  } finally {
    await server.close();
  }
});

test("POST /api/emergency-pause toggles pause state", async () => {
  const server = await startTestServer();
  try {
    const response = await fetch(`${server.baseUrl}/api/emergency-pause`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ paused: true })
    });
    const payload = await response.json();

    assert.equal(response.status, 200);
    assert.equal(payload.risk.emergencyPaused, true);
  } finally {
    await server.close();
  }
});

test("POST /api/emergency-pause rejects invalid payload", async () => {
  const server = await startTestServer();
  try {
    const response = await fetch(`${server.baseUrl}/api/emergency-pause`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ paused: "true" })
    });
    const payload = await response.json();

    assert.equal(response.status, 400);
    assert.equal(payload.error, "paused must be a boolean");
  } finally {
    await server.close();
  }
});
