# Prediction Copytrader Design

## Overview

`prediction-copytrader/` is a new standalone project inside this repository. It builds a Chrome extension plus a local Node executor for automated prediction-market monitoring, copy trading, scraping, risk control, and profit tracking.

The first version focuses on a working, auditable, locally controlled automation foundation:

- Chrome extension dashboard with five panels: Strategy, Monitor, Copy Trading, Scraper, and Profit.
- Local Node executor that performs long-running polling, signal generation, risk checks, signing, order submission, and audit logging.
- Polymarket supports real automated trading after explicit user setup and conservative risk checks.
- Predict.fun supports market monitoring, candidate discovery, and signal logging in the first version, but not real order execution.
- Private keys stay local, encrypted at rest, and are only decrypted into executor memory after user unlock.

## Project Structure

Create a new standalone project directory:

```text
prediction-copytrader/
  extension/
  executor/
  docs/
```

The existing World Cup web app remains separate. Existing files such as `app.js`, `styles.css`, `server.js`, and the current static pages are not converted into the extension.

Recommended detailed structure:

```text
prediction-copytrader/
  extension/
    manifest.json
    src/
      background/
      dashboard/
      services/
      styles/
  executor/
    package.json
    src/
      adapters/
        polymarket/
        predictfun/
      api/
      audit/
      risk/
      scraper/
      store/
      strategy/
      vault/
    data/
  docs/
    README.md
```

## Architecture

The system uses a two-layer local architecture.

### Chrome Extension

The extension is the control console. It provides the five user-facing panels, manages the local executor connection, displays wallet and runtime status, and sends configuration commands to the executor.

The extension does not perform long-running trading loops, direct scraping, or order submission. Chrome Manifest V3 service workers can sleep, so long-lived execution belongs in the local executor.

### Local Node Executor

The executor is the trading core. It runs on the user's machine and listens only on `127.0.0.1`.

Responsibilities:

- Store encrypted vault data.
- Unlock the trading wallet into memory after user password entry.
- Poll target addresses and market data.
- Run scraper rules.
- Generate normalized trade signals.
- Match signals against user strategies.
- Apply global, platform, market, address, strategy, and order-level risk checks.
- Sign and submit Polymarket CLOB orders.
- Record every signal, skip reason, order, error, and state transition.
- Serve local API endpoints for the extension dashboard.

The executor must not expose remote control by default.

## Panels

### Strategy

The Strategy panel is an extensible strategy center, not just a list of global settings.

Each strategy has:

- Applicability conditions: platform, market category, keywords, tags, liquidity, volume, time to close, target address, price range, and price movement.
- Trading logic: copy trading, reverse copy, near-close buy, price breakout, price pullback, buy YES, buy NO, sell, or observe only.
- Risk overrides: max order size, daily budget, max slippage, cooldown, max position, stop loss, take profit, and failure pause rules.

First built-in strategies:

- Conservative copy strategy: trades only whitelisted target addresses and whitelisted markets.
- Crypto market strategy: matches crypto-related categories and keywords such as crypto, bitcoin, ethereum, and solana.
- Sports market strategy: matches sports-related categories and keywords such as sports, football, soccer, and world cup.
- Near-close strategy: monitors markets close to resolution and can trade before closure if price, liquidity, whitelist, and risk checks pass.
- Observe strategy: records signals without placing orders, useful for testing new strategy settings.

The UI should support adding, copying, enabling, disabling, and deleting strategies. The first version uses form-based conditions rather than arbitrary user-supplied JavaScript. This prevents custom code from directly accessing private keys.

### Monitor

The Monitor panel is the operations cockpit.

It shows:

- Executor connection status.
- Wallet vault status: missing, locked, unlocked, or error.
- Polymarket adapter status.
- Predict.fun adapter status.
- Last polling time.
- Active scraper jobs.
- Pending signals.
- Recent warnings and errors.
- Emergency pause state.

The emergency pause button has highest priority. No strategy, scraper, copy-trading rule, or adapter can bypass it.

### Copy Trading

The Copy Trading panel manages target addresses.

Each target address supports:

- Address.
- Label.
- Platform.
- Enabled or disabled.
- Copy ratio.
- Per-address budget.
- Cooldown.
- Buy-only, sell-only, or both.
- Optional strategy binding.
- Optional category or market restrictions.

The executor polls target address activity and converts detected actions into normalized `TradeSignal` records. Signals then pass through strategy matching and risk control before any order can be submitted.

### Scraper

The Scraper panel manages configurable scraper rules.

Scraper rules discover markets, candidate addresses, and optional observation signals. They do not directly bypass strategy or risk control.

Each scraper rule has:

- Data source: Polymarket markets, Polymarket activity, Predict.fun markets, and future configured sources added through the same scraper-rule interface.
- Discovery filters: category, keywords, closing time, liquidity, volume, price movement, market status, and selected markets.
- Output target: candidate market, candidate address, signal, or observation.
- Bound strategy IDs.
- Safety settings.

First built-in scraper rules:

- Near-close market scanner: finds Polymarket markets close to closing while still open.
- Hot market scanner: finds markets with high volume or liquidity.
- Address discovery scanner: extracts active addresses from selected market activity.
- Predict.fun observation scanner: records market and candidate observations without real order execution.

Key principle: scrapers discover, strategies decide, risk control approves or blocks.

### Profit

The Profit panel reads local audit and order records.

It shows:

- Trade history.
- Filled, failed, skipped, and observed signals.
- Realized and estimated unrealized profit and loss.
- Strategy contribution.
- Target address contribution.
- Platform contribution.
- Estimated fee and slippage impact.
- Failure reasons.

The first version uses local order records and latest available market prices for estimates. It does not promise accounting-grade profit and loss precision.

## Key Workflows

### Initial Setup

1. User starts the local executor.
2. User opens the Chrome extension dashboard.
3. Extension connects to the local executor through `http://127.0.0.1:<port>`.
4. Executor and extension bind through a local API token.
5. User imports a small dedicated trading wallet private key.
6. User creates a trading password.
7. Executor encrypts the private key and stores it locally.
8. User unlocks the vault before any real trading.
9. User confirms the automatic trading risk notice.

### Strategy And Copy Trading

1. User configures global conservative risk settings.
2. User creates or enables one or more strategies.
3. User adds target addresses manually or imports candidates from the scraper panel.
4. Executor polls target address activity.
5. New activity becomes a normalized trade signal.
6. Strategy engine matches the signal.
7. Risk engine checks the signal.
8. If approved and platform is Polymarket, executor signs and submits the order.
9. Executor records the result.
10. Extension displays status and profit updates.

### Scraper-Driven Discovery

1. User enables a scraper rule.
2. Executor scans configured market sources.
3. Matching markets or addresses are added to candidate lists.
4. Candidate addresses must be manually accepted or bound by an enabled strategy before trading.
5. Scraper-generated signals default to observation mode unless a trade-enabled strategy is explicitly bound.
6. All outputs are audited.

## Vault And Key Safety

The private-key model is local encrypted trading-key storage.

Rules:

- The user should import a small dedicated trading wallet, not a main wallet.
- Private keys are never stored in plaintext.
- Private keys are never uploaded.
- Private keys are never logged.
- The encrypted vault is stored locally, for example in `prediction-copytrader/executor/data/vault.json`.
- The executor derives an encryption key from the user's trading password.
- The decrypted key only exists in executor memory after unlock.
- Locking the vault removes signing ability.
- Closing the executor clears decrypted memory state.
- Clearing the vault deletes local encrypted key material.

Extension and executor communication:

- Executor listens on `127.0.0.1`.
- Local API token is required.
- Sensitive values are redacted from logs and API responses.
- Remote access is disabled by default.

## Risk Model

Risk checks are layered and run before every real order.

### Global Risk

- Automatic trading master switch.
- Emergency pause.
- Daily total budget.
- Per-order maximum.
- Maximum slippage.
- Maximum open exposure.
- Consecutive failure pause.

### Platform Risk

- Polymarket can execute real trades in version one.
- Predict.fun is observe-only in version one.

### Market Risk

- Market whitelist.
- Category restrictions.
- Keyword restrictions.
- Closing-time restrictions.
- Liquidity and volume thresholds.
- Market status checks.

### Address Risk

- Per-target enable switch.
- Per-target budget.
- Per-target cooldown.
- Blacklist.
- Copy ratio.

### Strategy Risk

- Strategy mode: observe or trade.
- Strategy budget.
- Strategy slippage.
- Strategy cooldown.
- Stop loss and take profit rules when supported.
- Failure pause rules.

### Order Risk

- Wallet unlocked.
- Balance available.
- Allowance available when applicable.
- Market still open.
- Price within allowed slippage.
- Order size above platform minimum.
- Duplicate signal not already processed.

Default conservative settings:

- Max order: `10 USDC`.
- Daily budget: `100 USDC`.
- Max slippage: `1%`.
- Whitelisted markets only.
- Pause after 3 consecutive order failures.
- Do not retry closed markets, insufficient balance, failed signatures, or excessive price movement in a tight loop.
- Scraper-generated signals default to observation unless explicitly bound to a trade-enabled strategy.

## Data Model

### Strategy

```ts
type Strategy = {
  id: string;
  name: string;
  enabled: boolean;
  mode: "observe" | "trade";
  platforms: Array<"polymarket" | "predictfun">;
  categories: string[];
  keywords: string[];
  conditions: {
    minLiquidityUsd?: number;
    minVolumeUsd?: number;
    maxMinutesToClose?: number;
    minPrice?: number;
    maxPrice?: number;
    priceMovePct?: number;
  };
  action: {
    type: "copy" | "reverse_copy" | "near_close_buy" | "price_breakout" | "price_pullback";
    side: "buy_yes" | "buy_no" | "sell" | "any";
    copyRatio?: number;
  };
  risk: {
    maxOrderUsd: number;
    dailyBudgetUsd: number;
    maxSlippagePct: number;
    cooldownSeconds: number;
    maxPositionUsd?: number;
  };
};
```

### Scraper Rule

```ts
type ScraperRule = {
  id: string;
  name: string;
  enabled: boolean;
  source: "polymarket_markets" | "polymarket_activity" | "predictfun_markets";
  output: "candidate_market" | "candidate_address" | "signal" | "observation";
  filters: {
    categories: string[];
    keywords: string[];
    maxMinutesToClose?: number;
    minLiquidityUsd?: number;
    minVolumeUsd?: number;
    priceMovePct?: number;
  };
  boundStrategyIds: string[];
};
```

### Target Address

```ts
type TargetAddress = {
  id: string;
  platform: "polymarket" | "predictfun";
  address: string;
  label: string;
  enabled: boolean;
  copyRatio: number;
  maxDailyUsd: number;
  cooldownSeconds: number;
  allowedSides: "buy_only" | "sell_only" | "both";
  strategyIds: string[];
};
```

### Trade Signal

```ts
type TradeSignal = {
  id: string;
  platform: "polymarket" | "predictfun";
  source: "copy_address" | "scraper" | "manual";
  marketId: string;
  outcomeId?: string;
  side: "buy_yes" | "buy_no" | "sell";
  price: number;
  sizeUsd: number;
  targetAddress?: string;
  strategyId?: string;
  status: "observed" | "blocked" | "approved" | "submitted" | "filled" | "failed";
  reason?: string;
  createdAt: string;
};
```

## Storage

Use SQLite for the executor's first version. SQLite is better than loose JSON files for audit logs, order history, signal querying, profit summaries, and future migrations.

Local data categories:

- Encrypted vault.
- Settings.
- Strategies.
- Scraper rules.
- Target addresses.
- Candidate markets.
- Candidate addresses.
- Trade signals.
- Orders.
- Audit events.
- Runtime state.

## Platform Scope

### Polymarket

Version one supports:

- Market data.
- Address activity monitoring where available.
- Order construction.
- EIP-712 order signing through the local trading key.
- CLOB order submission.
- Order status tracking.
- Dry-run mode.
- Real trading only after explicit user enablement and passing all risk checks.

### Predict.fun

Version one supports:

- Market monitoring.
- Candidate discovery.
- Signal observation.
- Strategy matching in observe mode.
- Profit and opportunity notes where data is available.

Version one does not submit real Predict.fun orders.

## Testing Strategy

Implementation should use test-first development for production behavior.

Required test areas:

- Vault:
  - encrypted vault does not contain plaintext private key.
  - wrong password cannot unlock.
  - locked vault cannot sign.
  - clear vault removes encrypted material.
- Strategy:
  - category and keyword matching.
  - crypto-only and sports-only conditions.
  - near-close conditions.
  - liquidity, volume, and price bounds.
  - observe mode never emits executable orders.
- Scraper:
  - near-close sample markets produce candidate markets.
  - hot markets produce candidate markets.
  - activity samples produce candidate addresses.
  - Predict.fun scanner outputs observations only.
- Risk:
  - max order blocks oversized orders.
  - daily budget blocks excess orders.
  - slippage blocks price drift.
  - whitelist blocks non-whitelisted markets.
  - emergency pause blocks all real orders.
  - duplicate signal is blocked.
- Polymarket adapter:
  - market normalization from fixture data.
  - order request construction from approved signal.
  - adapter boundary uses mocked HTTP responses in tests.
  - no test places a real order.
- Extension:
  - five panels render.
  - executor disconnected state renders.
  - executor connected state renders.
  - emergency pause calls executor API.
  - vault locked and unlocked states render correctly.
- End-to-end dry run:
  - scraper discovery to signal.
  - signal to strategy match.
  - strategy match to risk approval or block.
  - dry-run order recorded without submitting real trade.

## Milestones

### M1: Project Skeleton

Create `prediction-copytrader/`, `extension/`, and `executor/`. The extension opens a dashboard with the five panels. The executor starts locally. The extension connects to the executor and displays status.

### M2: Vault And Security

Implement encrypted local vault, unlock, lock, clear vault, local API token binding, and sensitive log redaction. No real trade can execute while locked.

### M3: Strategy And Risk Engine

Implement strategy CRUD, strategy matching, observe and trade modes, global risk, market whitelist, strategy risk, and emergency pause.

### M4: Scraper Rules

Implement scraper rule CRUD and built-in scanners for near-close Polymarket markets, hot markets, activity-based address discovery, and Predict.fun observation.

### M5: Copy Trading Addresses

Implement manual target address management and conversion of target activity into normalized trade signals.

### M6: Polymarket Trading Adapter

Implement Polymarket market data, order construction, signing, submission, and status tracking. Real submission remains behind explicit trading enablement, unlocked vault, whitelist, and risk approval.

### M7: Profit And Audit

Implement signal, skip, order, failure, and profit displays from local audit data.

### M8: Verification And Documentation

Document local setup, risks, dry-run demo, test commands, and operational recovery. Verify disconnected executor, wrong password, emergency pause, budget exhaustion, closed markets, and observe mode behavior.

## Non-Goals

- No cloud-hosted executor in version one.
- No recommendation to import a main wallet private key.
- No Predict.fun real order execution in version one.
- No arbitrary user JavaScript strategy execution.
- No profit guarantee.
- No bypassing platform rules, regional restrictions, account restrictions, API rate limits, or access controls.
- No public remote control API by default.

## Open Technical Validation Items

These items must be validated during implementation planning and adapter work:

- Exact current Polymarket CLOB authentication and signing requirements.
- Exact Polymarket address activity data source and pagination behavior.
- Exact current Predict.fun public market data shape.
- Whether Predict.fun exposes any stable supported trading API suitable for a post-version-one trading adapter.
- Minimum Polymarket order sizes, allowance requirements, and practical rate limits.
- Chrome extension permissions needed for local executor communication and dashboard operation.
