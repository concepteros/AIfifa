import test from "node:test";
import assert from "node:assert/strict";

import { buildExecutorUrl, createExecutorClient } from "../src/services/executor-client.js";

test("buildExecutorUrl joins local base URL and API path", () => {
  assert.equal(
    buildExecutorUrl("http://127.0.0.1:4787", "/api/status"),
    "http://127.0.0.1:4787/api/status"
  );
});

test("createExecutorClient reads status", async () => {
  const requests = [];
  const client = createExecutorClient({
    baseUrl: "http://127.0.0.1:4787",
    fetchImpl: async (url, options) => {
      requests.push({ url, options });
      return {
        ok: true,
        json: async () => ({ risk: { emergencyPaused: false } })
      };
    }
  });

  const status = await client.getStatus();

  assert.deepEqual(status, { risk: { emergencyPaused: false } });
  assert.equal(requests[0].url, "http://127.0.0.1:4787/api/status");
});

test("createExecutorClient toggles emergency pause", async () => {
  const requests = [];
  const client = createExecutorClient({
    baseUrl: "http://127.0.0.1:4787",
    fetchImpl: async (url, options) => {
      requests.push({ url, options });
      return {
        ok: true,
        json: async () => ({ risk: { emergencyPaused: true } })
      };
    }
  });

  await client.setEmergencyPause(true);

  assert.equal(requests[0].url, "http://127.0.0.1:4787/api/emergency-pause");
  assert.equal(requests[0].options.method, "POST");
  assert.equal(requests[0].options.body, JSON.stringify({ paused: true }));
});

test("createExecutorClient throws readable errors for failed requests", async () => {
  const client = createExecutorClient({
    baseUrl: "http://127.0.0.1:4787",
    fetchImpl: async () => ({
      ok: false,
      status: 500,
      json: async () => ({ error: "boom" })
    })
  });

  await assert.rejects(
    () => client.getStatus(),
    /boom/
  );
});
