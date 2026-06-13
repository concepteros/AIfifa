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
