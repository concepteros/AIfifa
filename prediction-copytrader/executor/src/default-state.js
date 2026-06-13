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
