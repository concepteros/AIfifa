# Prediction Copytrader Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the standalone `prediction-copytrader/` foundation with a local executor status API and a Chrome extension dashboard containing the five approved panels.

**Architecture:** This first plan implements M1 only. The executor is a dependency-free Node ESM HTTP server that listens on `127.0.0.1` and exposes health, status, and emergency-pause endpoints. The extension is a vanilla Manifest V3 dashboard that calls the local executor and renders Strategy, Monitor, Copy Trading, Scraper, and Profit panels without yet implementing vaults, scraping, or real trading.

**Tech Stack:** Node.js ESM, Node built-in `node:test`, vanilla Chrome Extension Manifest V3, HTML, CSS, browser ES modules.

---

## Scope

This plan intentionally does not implement private-key storage, strategy CRUD, scraper jobs, Polymarket trading, Predict.fun integration, SQLite, or real order submission. Those are separate follow-up plans after this foundation is running and verified.

## File Structure

- Create: `prediction-copytrader/package.json`
  - Root scripts for executor startup, syntax checks, and tests.
- Create: `prediction-copytrader/README.md`
  - Local development and extension loading notes.
- Create: `prediction-copytrader/executor/src/default-state.js`
  - Default runtime status and panel summary data.
- Create: `prediction-copytrader/executor/src/runtime-state.js`
  - In-memory state creation, status reading, and emergency-pause mutation.
- Create: `prediction-copytrader/executor/src/http-utils.js`
  - JSON responses, request body parsing, and route helpers.
- Create: `prediction-copytrader/executor/src/server.js`
  - Local HTTP API.
- Create: `prediction-copytrader/executor/test/runtime-state.test.js`
  - Runtime state tests.
- Create: `prediction-copytrader/executor/test/server.test.js`
  - Executor API tests.
- Create: `prediction-copytrader/extension/manifest.json`
  - Manifest V3 extension config.
- Create: `prediction-copytrader/extension/src/background/service-worker.js`
  - Minimal background service worker.
- Create: `prediction-copytrader/extension/src/services/executor-client.js`
  - Local executor API client.
- Create: `prediction-copytrader/extension/src/dashboard/dashboard.html`
  - Dashboard markup.
- Create: `prediction-copytrader/extension/src/dashboard/dashboard.css`
  - Dashboard styles.
- Create: `prediction-copytrader/extension/src/dashboard/dashboard.js`
  - Five-panel rendering and emergency pause action.
- Create: `prediction-copytrader/extension/test/executor-client.test.js`
  - Extension API client tests.

## API Contract

The foundation executor exposes these endpoints:

- `GET /health`
  - Returns `{ "ok": true, "service": "prediction-copytrader-executor" }`.
- `GET /api/status`
  - Returns runtime status used by the dashboard.
- `POST /api/emergency-pause`
  - Body: `{ "paused": true }` or `{ "paused": false }`.
  - Returns the updated status.

Default status shape:

```js
{
  service: "prediction-copytrader-executor",
  version: "0.1.0",
  executor: {
    connected: true,
    host: "127.0.0.1",
    port: 4787,
    startedAt: "2026-06-14T00:00:00.000Z",
    lastHeartbeatAt: "2026-06-14T00:00:00.000Z"
  },
  wallet: {
    vault: "missing",
    address: "",
    canSign: false
  },
  platforms: {
    polymarket: { mode: "dry-run", status: "not-configured" },
    predictfun: { mode: "observe", status: "not-configured" }
  },
  risk: {
    emergencyPaused: false,
    maxOrderUsd: 10,
    dailyBudgetUsd: 100,
    maxSlippagePct: 1,
    whitelistOnly: true
  },
  panels: {
    strategy: { enabled: 0, observing: 1, trading: 0 },
    monitor: { pendingSignals: 0, warnings: 0, errors: 0 },
    copyTrading: { targetAddresses: 0, enabledTargets: 0 },
    scraper: { rules: 0, activeRules: 0, candidates: 0 },
    profit: { trades: 0, realizedPnlUsd: 0, estimatedUnrealizedPnlUsd: 0 }
  }
}
```

## Task 1: Scaffold Standalone Project

**Files:**
- Create: `prediction-copytrader/package.json`
- Create: `prediction-copytrader/README.md`

- [ ] **Step 1: Write the initial package manifest**

Create `prediction-copytrader/package.json`:

```json
{
  "name": "prediction-copytrader",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "start:executor": "node executor/src/server.js",
    "test": "node --test executor/test extension/test",
    "check": "node --check executor/src/server.js && node --check extension/src/background/service-worker.js && node --check extension/src/services/executor-client.js && node --check extension/src/dashboard/dashboard.js"
  }
}
```

- [ ] **Step 2: Write the project README**

Create `prediction-copytrader/README.md`:

```md
# Prediction Copytrader

Standalone Chrome extension plus local Node executor for prediction-market monitoring and controlled copy-trading automation.

## Local Executor

```bash
npm run start:executor
```

The executor listens on `http://127.0.0.1:4787` by default.

## Chrome Extension

Load `prediction-copytrader/extension` as an unpacked extension in Chrome.

The dashboard opens from the extension action and calls the local executor status API.

## Verification

```bash
npm test
npm run check
```
```

- [ ] **Step 3: Verify package metadata can be read**

Run:

```bash
node -e "const pkg=require('./prediction-copytrader/package.json'); console.log(pkg.name)"
```

Expected:

```text
prediction-copytrader
```

- [ ] **Step 4: Commit**

```bash
git add prediction-copytrader/package.json prediction-copytrader/README.md
git commit -m "chore: scaffold prediction copytrader project"
```

## Task 2: Add Runtime State Tests

**Files:**
- Create: `prediction-copytrader/executor/test/runtime-state.test.js`
- Task 3 creates: `prediction-copytrader/executor/src/default-state.js`
- Task 3 creates: `prediction-copytrader/executor/src/runtime-state.js`

- [ ] **Step 1: Write failing runtime state tests**

Create `prediction-copytrader/executor/test/runtime-state.test.js`:

```js
import test from "node:test";
import assert from "node:assert/strict";

import { createRuntimeState, getStatus, setEmergencyPause } from "../src/runtime-state.js";

test("createRuntimeState returns conservative default status", () => {
  const runtime = createRuntimeState({ now: () => new Date("2026-06-14T00:00:00.000Z") });
  const status = getStatus(runtime);

  assert.equal(status.service, "prediction-copytrader-executor");
  assert.equal(status.wallet.vault, "missing");
  assert.equal(status.wallet.canSign, false);
  assert.equal(status.platforms.polymarket.mode, "dry-run");
  assert.equal(status.platforms.predictfun.mode, "observe");
  assert.equal(status.risk.maxOrderUsd, 10);
  assert.equal(status.risk.dailyBudgetUsd, 100);
  assert.equal(status.risk.maxSlippagePct, 1);
  assert.equal(status.risk.whitelistOnly, true);
  assert.equal(status.risk.emergencyPaused, false);
});

test("setEmergencyPause updates status without mutating returned snapshots", () => {
  const runtime = createRuntimeState({ now: () => new Date("2026-06-14T00:00:00.000Z") });
  const before = getStatus(runtime);

  const paused = setEmergencyPause(runtime, true);
  const after = getStatus(runtime);

  assert.equal(before.risk.emergencyPaused, false);
  assert.equal(paused.risk.emergencyPaused, true);
  assert.equal(after.risk.emergencyPaused, true);
});

test("setEmergencyPause rejects non-boolean values", () => {
  const runtime = createRuntimeState({ now: () => new Date("2026-06-14T00:00:00.000Z") });

  assert.throws(
    () => setEmergencyPause(runtime, "yes"),
    /paused must be a boolean/
  );
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd prediction-copytrader
npm test
```

Expected: FAIL because `executor/src/runtime-state.js` does not exist.

## Task 3: Implement Runtime State

**Files:**
- Create: `prediction-copytrader/executor/src/default-state.js`
- Create: `prediction-copytrader/executor/src/runtime-state.js`
- Test: `prediction-copytrader/executor/test/runtime-state.test.js`

- [ ] **Step 1: Implement default state factory**

Create `prediction-copytrader/executor/src/default-state.js`:

```js
export const DEFAULT_PORT = 4787;

export function createDefaultStatus({ now = () => new Date(), port = DEFAULT_PORT } = {}) {
  const timestamp = now().toISOString();

  return {
    service: "prediction-copytrader-executor",
    version: "0.1.0",
    executor: {
      connected: true,
      host: "127.0.0.1",
      port,
      startedAt: timestamp,
      lastHeartbeatAt: timestamp
    },
    wallet: {
      vault: "missing",
      address: "",
      canSign: false
    },
    platforms: {
      polymarket: { mode: "dry-run", status: "not-configured" },
      predictfun: { mode: "observe", status: "not-configured" }
    },
    risk: {
      emergencyPaused: false,
      maxOrderUsd: 10,
      dailyBudgetUsd: 100,
      maxSlippagePct: 1,
      whitelistOnly: true
    },
    panels: {
      strategy: { enabled: 0, observing: 1, trading: 0 },
      monitor: { pendingSignals: 0, warnings: 0, errors: 0 },
      copyTrading: { targetAddresses: 0, enabledTargets: 0 },
      scraper: { rules: 0, activeRules: 0, candidates: 0 },
      profit: { trades: 0, realizedPnlUsd: 0, estimatedUnrealizedPnlUsd: 0 }
    }
  };
}
```

- [ ] **Step 2: Implement runtime state helpers**

Create `prediction-copytrader/executor/src/runtime-state.js`:

```js
import { createDefaultStatus } from "./default-state.js";

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

export function createRuntimeState(options = {}) {
  return {
    status: createDefaultStatus(options)
  };
}

export function getStatus(runtime) {
  return clone(runtime.status);
}

export function setEmergencyPause(runtime, paused) {
  if (typeof paused !== "boolean") {
    throw new TypeError("paused must be a boolean");
  }

  runtime.status.risk.emergencyPaused = paused;
  runtime.status.executor.lastHeartbeatAt = new Date().toISOString();
  return getStatus(runtime);
}
```

- [ ] **Step 3: Run runtime tests**

Run:

```bash
cd prediction-copytrader
npm test -- executor/test/runtime-state.test.js
```

Expected: PASS for all runtime state tests.

- [ ] **Step 4: Commit**

```bash
git add prediction-copytrader/executor/src/default-state.js prediction-copytrader/executor/src/runtime-state.js prediction-copytrader/executor/test/runtime-state.test.js
git commit -m "feat: add executor runtime state"
```

## Task 4: Add Executor Server Tests

**Files:**
- Create: `prediction-copytrader/executor/test/server.test.js`
- Task 5 creates: `prediction-copytrader/executor/src/http-utils.js`
- Task 5 creates: `prediction-copytrader/executor/src/server.js`

- [ ] **Step 1: Write failing API tests**

Create `prediction-copytrader/executor/test/server.test.js`:

```js
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd prediction-copytrader
npm test -- executor/test/server.test.js
```

Expected: FAIL because `executor/src/server.js` does not exist.

## Task 5: Implement Executor Server

**Files:**
- Create: `prediction-copytrader/executor/src/http-utils.js`
- Create: `prediction-copytrader/executor/src/server.js`
- Test: `prediction-copytrader/executor/test/server.test.js`

- [ ] **Step 1: Add HTTP utilities**

Create `prediction-copytrader/executor/src/http-utils.js`:

```js
export function sendJson(response, statusCode, payload) {
  response.writeHead(statusCode, {
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "GET,POST,OPTIONS",
    "access-control-allow-headers": "content-type",
    "cache-control": "no-store",
    "content-type": "application/json; charset=utf-8"
  });
  response.end(JSON.stringify(payload));
}

export async function readJsonBody(request) {
  let body = "";

  for await (const chunk of request) {
    body += chunk;
    if (body.length > 20_000) {
      throw new Error("request body too large");
    }
  }

  return JSON.parse(body || "{}");
}
```

- [ ] **Step 2: Implement local executor server**

Create `prediction-copytrader/executor/src/server.js`:

```js
import http from "node:http";

import { DEFAULT_PORT } from "./default-state.js";
import { sendJson, readJsonBody } from "./http-utils.js";
import { createRuntimeState, getStatus, setEmergencyPause } from "./runtime-state.js";

const HOST = "127.0.0.1";

export function createServer({ runtime = createRuntimeState() } = {}) {
  return http.createServer(async (request, response) => {
    try {
      if (request.method === "OPTIONS") {
        return sendJson(response, 204, {});
      }

      const url = new URL(request.url || "/", `http://${request.headers.host || HOST}`);

      if (request.method === "GET" && url.pathname === "/health") {
        return sendJson(response, 200, {
          ok: true,
          service: "prediction-copytrader-executor"
        });
      }

      if (request.method === "GET" && url.pathname === "/api/status") {
        return sendJson(response, 200, getStatus(runtime));
      }

      if (request.method === "POST" && url.pathname === "/api/emergency-pause") {
        const payload = await readJsonBody(request);
        return sendJson(response, 200, setEmergencyPause(runtime, payload.paused));
      }

      return sendJson(response, 404, { error: "not found" });
    } catch (error) {
      return sendJson(response, 400, { error: error.message || "request failed" });
    }
  });
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const port = Number(process.env.PORT || DEFAULT_PORT);
  const server = createServer({ runtime: createRuntimeState({ port }) });

  server.listen(port, HOST, () => {
    console.log(`prediction-copytrader executor listening on http://${HOST}:${port}`);
  });
}
```

- [ ] **Step 3: Run server tests**

Run:

```bash
cd prediction-copytrader
npm test -- executor/test/server.test.js
```

Expected: PASS for all executor server tests.

- [ ] **Step 4: Run syntax checks**

Run:

```bash
cd prediction-copytrader
npm run check
```

Expected during this task: FAIL because extension files are not created yet. This confirms executor syntax is valid only if the failure mentions missing extension files.

- [ ] **Step 5: Commit**

```bash
git add prediction-copytrader/executor/src/http-utils.js prediction-copytrader/executor/src/server.js prediction-copytrader/executor/test/server.test.js
git commit -m "feat: add local executor status api"
```

## Task 6: Add Extension API Client Tests

**Files:**
- Create: `prediction-copytrader/extension/test/executor-client.test.js`
- Task 7 creates: `prediction-copytrader/extension/src/services/executor-client.js`

- [ ] **Step 1: Write failing extension client tests**

Create `prediction-copytrader/extension/test/executor-client.test.js`:

```js
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd prediction-copytrader
npm test -- extension/test/executor-client.test.js
```

Expected: FAIL because `extension/src/services/executor-client.js` does not exist.

## Task 7: Implement Extension API Client And Manifest

**Files:**
- Create: `prediction-copytrader/extension/src/services/executor-client.js`
- Create: `prediction-copytrader/extension/manifest.json`
- Create: `prediction-copytrader/extension/src/background/service-worker.js`
- Test: `prediction-copytrader/extension/test/executor-client.test.js`

- [ ] **Step 1: Implement executor API client**

Create `prediction-copytrader/extension/src/services/executor-client.js`:

```js
const DEFAULT_EXECUTOR_URL = "http://127.0.0.1:4787";

export function buildExecutorUrl(baseUrl, pathname) {
  return new URL(pathname, baseUrl).toString();
}

async function readJsonResponse(response) {
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `Executor request failed with ${response.status}`);
  }
  return payload;
}

export function createExecutorClient({ baseUrl = DEFAULT_EXECUTOR_URL, fetchImpl = fetch } = {}) {
  return {
    getStatus() {
      return fetchImpl(buildExecutorUrl(baseUrl, "/api/status")).then(readJsonResponse);
    },
    setEmergencyPause(paused) {
      return fetchImpl(buildExecutorUrl(baseUrl, "/api/emergency-pause"), {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ paused })
      }).then(readJsonResponse);
    }
  };
}
```

- [ ] **Step 2: Add Manifest V3 config**

Create `prediction-copytrader/extension/manifest.json`:

```json
{
  "manifest_version": 3,
  "name": "Prediction Copytrader",
  "version": "0.1.0",
  "description": "Local dashboard for prediction-market monitoring and controlled copy-trading automation.",
  "action": {
    "default_title": "Prediction Copytrader"
  },
  "background": {
    "service_worker": "src/background/service-worker.js",
    "type": "module"
  },
  "permissions": ["storage"],
  "host_permissions": ["http://127.0.0.1:4787/*"],
  "chrome_url_overrides": {},
  "web_accessible_resources": []
}
```

- [ ] **Step 3: Add service worker**

Create `prediction-copytrader/extension/src/background/service-worker.js`:

```js
chrome.action.onClicked.addListener(() => {
  chrome.tabs.create({
    url: chrome.runtime.getURL("src/dashboard/dashboard.html")
  });
});
```

- [ ] **Step 4: Run extension client tests**

Run:

```bash
cd prediction-copytrader
npm test -- extension/test/executor-client.test.js
```

Expected: PASS for all extension client tests.

- [ ] **Step 5: Commit**

```bash
git add prediction-copytrader/extension/src/services/executor-client.js prediction-copytrader/extension/manifest.json prediction-copytrader/extension/src/background/service-worker.js prediction-copytrader/extension/test/executor-client.test.js
git commit -m "feat: add extension executor client"
```

## Task 8: Add Dashboard UI

**Files:**
- Create: `prediction-copytrader/extension/src/dashboard/dashboard.html`
- Create: `prediction-copytrader/extension/src/dashboard/dashboard.css`
- Create: `prediction-copytrader/extension/src/dashboard/dashboard.js`

- [ ] **Step 1: Create dashboard HTML**

Create `prediction-copytrader/extension/src/dashboard/dashboard.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Prediction Copytrader</title>
    <link rel="stylesheet" href="./dashboard.css" />
  </head>
  <body>
    <aside class="sidebar">
      <div>
        <p class="eyebrow">Local Executor</p>
        <h1>Prediction Copytrader</h1>
      </div>
      <nav class="tabs" aria-label="Panels">
        <button class="tab is-active" type="button" data-panel="strategy">策略</button>
        <button class="tab" type="button" data-panel="monitor">监控</button>
        <button class="tab" type="button" data-panel="copyTrading">跟单</button>
        <button class="tab" type="button" data-panel="scraper">刮刀</button>
        <button class="tab" type="button" data-panel="profit">收益</button>
      </nav>
    </aside>
    <main class="main">
      <header class="topbar">
        <div>
          <p id="connectionLabel" class="eyebrow">Connecting</p>
          <h2 id="panelTitle">策略</h2>
        </div>
        <button id="pauseButton" class="danger" type="button">紧急暂停</button>
      </header>
      <section id="statusBanner" class="status-banner">正在连接本地执行器...</section>
      <section id="panelContent" class="panel-grid"></section>
    </main>
    <script type="module" src="./dashboard.js"></script>
  </body>
</html>
```

- [ ] **Step 2: Create dashboard CSS**

Create `prediction-copytrader/extension/src/dashboard/dashboard.css`:

```css
:root {
  color-scheme: light;
  --bg: #f7f8fb;
  --panel: #ffffff;
  --text: #17202a;
  --muted: #667085;
  --line: #d9e0ea;
  --accent: #0f766e;
  --danger: #b42318;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-height: 100vh;
  display: grid;
  grid-template-columns: 260px 1fr;
  background: var(--bg);
  color: var(--text);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.sidebar {
  padding: 24px;
  border-right: 1px solid var(--line);
  background: #ffffff;
}

.eyebrow {
  margin: 0 0 6px;
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}

h1,
h2,
h3,
p {
  margin-top: 0;
}

h1 {
  font-size: 24px;
  line-height: 1.1;
}

.tabs {
  display: grid;
  gap: 8px;
  margin-top: 28px;
}

.tab,
button {
  height: 40px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #ffffff;
  color: var(--text);
  font-weight: 700;
  cursor: pointer;
}

.tab.is-active {
  border-color: var(--accent);
  color: var(--accent);
  background: #ecfdf8;
}

.main {
  padding: 24px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.danger {
  min-width: 112px;
  border-color: rgba(180, 35, 24, 0.3);
  color: var(--danger);
}

.status-banner {
  margin: 20px 0;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #ffffff;
  color: var(--muted);
}

.status-banner.is-paused {
  border-color: rgba(180, 35, 24, 0.35);
  color: var(--danger);
}

.panel-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.metric-card {
  min-height: 120px;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
}

.metric-card strong {
  display: block;
  font-size: 28px;
  line-height: 1.1;
}

@media (max-width: 760px) {
  body {
    grid-template-columns: 1fr;
  }

  .sidebar {
    border-right: 0;
    border-bottom: 1px solid var(--line);
  }
}
```

- [ ] **Step 3: Create dashboard JavaScript**

Create `prediction-copytrader/extension/src/dashboard/dashboard.js`:

```js
import { createExecutorClient } from "../services/executor-client.js";

const client = createExecutorClient();
let activePanel = "strategy";
let latestStatus = null;

const panelTitles = {
  strategy: "策略",
  monitor: "监控",
  copyTrading: "跟单",
  scraper: "刮刀",
  profit: "收益"
};

const panelMetrics = {
  strategy: [
    ["启用策略", (status) => status.panels.strategy.enabled],
    ["观察策略", (status) => status.panels.strategy.observing],
    ["交易策略", (status) => status.panels.strategy.trading]
  ],
  monitor: [
    ["待处理信号", (status) => status.panels.monitor.pendingSignals],
    ["警告", (status) => status.panels.monitor.warnings],
    ["错误", (status) => status.panels.monitor.errors]
  ],
  copyTrading: [
    ["目标地址", (status) => status.panels.copyTrading.targetAddresses],
    ["启用地址", (status) => status.panels.copyTrading.enabledTargets],
    ["单笔上限", (status) => `${status.risk.maxOrderUsd} USDC`]
  ],
  scraper: [
    ["刮刀规则", (status) => status.panels.scraper.rules],
    ["运行规则", (status) => status.panels.scraper.activeRules],
    ["候选项", (status) => status.panels.scraper.candidates]
  ],
  profit: [
    ["交易数", (status) => status.panels.profit.trades],
    ["已实现", (status) => `${status.panels.profit.realizedPnlUsd} USDC`],
    ["未实现估算", (status) => `${status.panels.profit.estimatedUnrealizedPnlUsd} USDC`]
  ]
};

function renderPanel(status) {
  document.querySelector("#panelTitle").textContent = panelTitles[activePanel];
  document.querySelector("#panelContent").innerHTML = panelMetrics[activePanel].map(([label, read]) => `
    <article class="metric-card">
      <p class="eyebrow">${label}</p>
      <strong>${read(status)}</strong>
    </article>
  `).join("");
}

function renderStatus(status) {
  latestStatus = status;
  const banner = document.querySelector("#statusBanner");
  const paused = status.risk.emergencyPaused;
  document.querySelector("#connectionLabel").textContent = "Connected";
  document.querySelector("#pauseButton").textContent = paused ? "解除暂停" : "紧急暂停";
  banner.classList.toggle("is-paused", paused);
  banner.textContent = paused
    ? "自动交易已紧急暂停。"
    : `本地执行器已连接，Polymarket ${status.platforms.polymarket.mode}，Predict.fun ${status.platforms.predictfun.mode}。`;
  renderPanel(status);
}

function renderDisconnected(error) {
  latestStatus = null;
  document.querySelector("#connectionLabel").textContent = "Disconnected";
  document.querySelector("#statusBanner").textContent = `无法连接本地执行器：${error.message}`;
  document.querySelector("#panelContent").innerHTML = "";
}

async function refreshStatus() {
  try {
    renderStatus(await client.getStatus());
  } catch (error) {
    renderDisconnected(error);
  }
}

document.querySelectorAll("[data-panel]").forEach((button) => {
  button.addEventListener("click", () => {
    activePanel = button.dataset.panel;
    document.querySelectorAll("[data-panel]").forEach((item) => {
      item.classList.toggle("is-active", item === button);
    });
    if (latestStatus) renderPanel(latestStatus);
  });
});

document.querySelector("#pauseButton").addEventListener("click", async () => {
  if (!latestStatus) return;
  try {
    renderStatus(await client.setEmergencyPause(!latestStatus.risk.emergencyPaused));
  } catch (error) {
    renderDisconnected(error);
  }
});

refreshStatus();
setInterval(refreshStatus, 5000);
```

- [ ] **Step 4: Run syntax checks**

Run:

```bash
cd prediction-copytrader
npm run check
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add prediction-copytrader/extension/src/dashboard/dashboard.html prediction-copytrader/extension/src/dashboard/dashboard.css prediction-copytrader/extension/src/dashboard/dashboard.js
git commit -m "feat: add extension dashboard shell"
```

## Task 9: Full Foundation Verification

**Files:**
- Verify all files created by Tasks 1-8.

- [ ] **Step 1: Run all tests**

Run:

```bash
cd prediction-copytrader
npm test
```

Expected: PASS for executor and extension tests.

- [ ] **Step 2: Run syntax checks**

Run:

```bash
cd prediction-copytrader
npm run check
```

Expected: PASS.

- [ ] **Step 3: Start the executor manually**

Run:

```bash
cd prediction-copytrader
npm run start:executor
```

Expected output:

```text
prediction-copytrader executor listening on http://127.0.0.1:4787
```

- [ ] **Step 4: Verify health endpoint in another terminal**

Run:

```bash
node -e "fetch('http://127.0.0.1:4787/health').then(r=>r.json()).then(console.log)"
```

Expected output includes:

```text
{ ok: true, service: 'prediction-copytrader-executor' }
```

- [ ] **Step 5: Stop the executor**

Stop the running `npm run start:executor` process with `Ctrl+C`.

- [ ] **Step 6: Check git status**

Run:

```bash
git status --short
```

Expected: no unstaged files under `prediction-copytrader/` after the task commits. Existing unrelated files such as root `app.js`, root `styles.css`, or local server logs may still be present and must not be modified or reverted.

## Self-Review Checklist

- [ ] The plan implements the approved M1 foundation milestone.
- [ ] The executor has status and emergency-pause APIs.
- [ ] The extension has Strategy, Monitor, Copy Trading, Scraper, and Profit panels.
- [ ] The dashboard can call the executor through `http://127.0.0.1:4787`.
- [ ] No private-key storage is implemented in this plan.
- [ ] No real trading is implemented in this plan.
- [ ] Predict.fun remains observe-only by design.
- [ ] All production behavior in this plan has a failing test before implementation where practical.
- [ ] The plan contains no placeholder tasks.

## Follow-Up Plans

After this foundation plan is implemented and verified, write separate implementation plans for:

1. Vault and local API token binding.
2. Strategy and risk engine.
3. Scraper rules and candidate discovery.
4. Copy-trading target addresses.
5. Polymarket dry-run and trading adapter.
6. Profit and audit storage.
