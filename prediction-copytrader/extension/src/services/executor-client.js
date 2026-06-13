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
