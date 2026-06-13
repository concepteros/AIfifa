import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { DEFAULT_PORT } from "./default-state.js";
import { sendJson, readJsonBody } from "./http-utils.js";
import { createRuntimeState, getStatus, setEmergencyPause } from "./runtime-state.js";

const HOST = "127.0.0.1";

export function isDirectRun(metaUrl, argvPath) {
  if (!argvPath) return false;
  return fileURLToPath(metaUrl) === path.resolve(argvPath);
}

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

if (isDirectRun(import.meta.url, process.argv[1])) {
  const port = Number(process.env.PORT || DEFAULT_PORT);
  const server = createServer({ runtime: createRuntimeState({ port }) });

  server.listen(port, HOST, () => {
    console.log(`prediction-copytrader executor listening on http://${HOST}:${port}`);
  });
}
