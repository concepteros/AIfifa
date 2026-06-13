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
