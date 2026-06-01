const POLYMARKET_BASE_URL = "https://gamma-api.polymarket.com";
const DEFAULT_POLYMARKET_QUERY = "2026 world cup winner";
const ACCESS_UNLOCK_KEY = "fifa2026PremiumUnlocked";
const SOLANA_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v";
const SOLANA_USDC_RECIPIENT = "EwAh2VbsbgG2xWsFsDYMjmCUqq48cSkms1HATZDi3Vgq";
const PREMIUM_PRICE_USDC = "19.9";

const TEAM_ALIASES = {
  "United States": ["usa", "u.s.", "usmnt", "united states", "america"],
  "Korea Republic": ["south korea", "korea republic", "korea"],
  "IR Iran": ["iran", "ir iran"],
  "Turkiye": ["turkey", "turkiye", "tuerkiye"],
  "Cote d'Ivoire": ["ivory coast", "cote d'ivoire", "cote divoire"],
  "Cabo Verde": ["cape verde", "cabo verde"],
  "Congo DR": ["dr congo", "congo dr", "democratic republic of congo"],
  "Curacao": ["curacao", "curacao"]
};

const state = {
  data: structuredClone(window.WORLD_CUP_DATA),
  query: "",
  group: "all",
  sort: "probability",
  historyView: "editions",
  polymarket: {
    query: localStorage.getItem("wcPolymarketQuery") || DEFAULT_POLYMARKET_QUERY,
    lastMarkets: [],
    lastEventCount: 0
  }
};

const els = {
  searchInput: document.querySelector("#searchInput"),
  groupFilter: document.querySelector("#groupFilter"),
  sortSelect: document.querySelector("#sortSelect"),
  contendersList: document.querySelector("#contendersList"),
  teamGrid: document.querySelector("#teamGrid"),
  mvpList: document.querySelector("#mvpList"),
  historyContent: document.querySelector("#historyContent"),
  bracketGrid: document.querySelector("#bracketGrid"),
  bracketUpdatedAt: document.querySelector("#bracketUpdatedAt"),
  updatedAt: document.querySelector("#updatedAt"),
  refreshButton: document.querySelector("#refreshButton"),
  refreshState: document.querySelector("#refreshState"),
  editionCount: document.querySelector("#editionCount"),
  walletButton: document.querySelector("#walletButton"),
  walletButtonText: document.querySelector("#walletButtonText"),
  walletMenu: document.querySelector("#walletMenu"),
  walletCloseButton: document.querySelector("#walletCloseButton"),
  walletOptions: document.querySelector("#walletOptions"),
  walletConnected: document.querySelector("#walletConnected"),
  walletConnectedLabel: document.querySelector("#walletConnectedLabel"),
  walletDisconnectButton: document.querySelector("#walletDisconnectButton"),
  walletMessage: document.querySelector("#walletMessage"),
  accessGate: document.querySelector("#accessGate"),
  accessWalletOptions: document.querySelector("#accessWalletOptions"),
  accessPayment: document.querySelector("#accessPayment"),
  accessWalletAddress: document.querySelector("#accessWalletAddress"),
  accessPayButton: document.querySelector("#accessPayButton"),
  accessCheckButton: document.querySelector("#accessCheckButton"),
  accessMessage: document.querySelector("#accessMessage")
};

const walletState = {
  provider: null,
  address: "",
  name: "",
  paymentPoll: null
};

function normalize(text) {
  return String(text || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function matchQuery(item, query) {
  if (!query) return true;
  return normalize(JSON.stringify(item)).includes(normalize(query));
}

function formatDate(value) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

function parseMaybeJson(value) {
  if (Array.isArray(value)) return value;
  if (typeof value !== "string") return [];
  try {
    return JSON.parse(value);
  } catch {
    return value.split(",").map((item) => item.trim()).filter(Boolean);
  }
}

function asPercent(price) {
  const number = Number(price);
  if (!Number.isFinite(number)) return null;
  return Math.max(0, Math.min(100, number <= 1 ? number * 100 : number));
}

function aliasesFor(team) {
  return [team.name, team.code, ...(TEAM_ALIASES[team.name] || [])].map(normalize);
}

function teamMentioned(text, team) {
  const source = normalize(text);
  return aliasesFor(team).some((alias) => alias && source.includes(alias));
}

function isWinnerMarket(market) {
  const text = normalize([market.question, market.title, market.slug, market.description].join(" "));
  return text.includes("world cup") && (text.includes("winner") || text.includes("win") || text.includes("champion"));
}

function marketUrl(market) {
  return market.slug ? `https://polymarket.com/event/${market.slug}` : "https://polymarket.com";
}

function flattenMarkets(searchPayload) {
  const markets = [];
  (searchPayload.events || []).forEach((event) => {
    (event.markets || []).forEach((market) => {
      markets.push({
        ...market,
        eventTitle: event.title,
        eventSlug: event.slug,
        eventVolume: event.volume || event.volume24hr
      });
    });
  });
  (searchPayload.markets || []).forEach((market) => markets.push(market));
  return markets.filter((market) => market && !market.closed && market.active !== false);
}

function pricesFromMarket(market) {
  const outcomes = parseMaybeJson(market.outcomes);
  const prices = parseMaybeJson(market.outcomePrices);
  return outcomes
    .map((outcome, index) => ({
      outcome: String(outcome),
      probability: asPercent(prices[index])
    }))
    .filter((entry) => entry.probability !== null);
}

function probabilityFromMarket(team, market) {
  const entries = pricesFromMarket(market);
  if (!entries.length || !isWinnerMarket(market)) return null;

  const directOutcome = entries.find((entry) => teamMentioned(entry.outcome, team));
  if (directOutcome) {
    return {
      probability: directOutcome.probability,
      source: market.question || market.eventTitle || "Polymarket",
      url: marketUrl(market),
      volume: Number(market.volumeNum || market.volume || market.eventVolume || 0)
    };
  }

  const yesOutcome = entries.find((entry) => normalize(entry.outcome) === "yes");
  if (yesOutcome && teamMentioned([market.question, market.title, market.slug].join(" "), team)) {
    return {
      probability: yesOutcome.probability,
      source: market.question || market.eventTitle || "Polymarket",
      url: marketUrl(market),
      volume: Number(market.volumeNum || market.volume || market.eventVolume || 0)
    };
  }

  return null;
}

function applyPolymarketMarkets(markets) {
  const next = structuredClone(state.data);
  let matched = 0;

  next.teams = next.teams.map((team) => {
    const candidates = markets
      .map((market) => probabilityFromMarket(team, market))
      .filter(Boolean)
      .sort((a, b) => b.volume - a.volume);

    if (!candidates.length) {
      return {
        ...team,
        marketSource: "未匹配 Polymarket 市场",
        marketUrl: ""
      };
    }

    matched += 1;
    const best = candidates[0];
    return {
      ...team,
      probability: Number(best.probability.toFixed(1)),
      marketSource: best.source,
      marketUrl: best.url,
      marketVolume: best.volume
    };
  });

  next.meta = {
    ...next.meta,
    updatedAt: new Date().toISOString(),
    status: "polymarket",
    note: `Polymarket Gamma API: ${matched} teams matched from ${markets.length} active markets.`
  };

  state.data = next;
  return matched;
}

async function fetchPolymarketMarkets() {
  const params = new URLSearchParams({
    q: state.polymarket.query || DEFAULT_POLYMARKET_QUERY,
    events_status: "active",
    keep_closed_markets: "0",
    limit_per_type: "20",
    search_profiles: "false",
    search_tags: "false"
  });

  const response = await fetch(`${POLYMARKET_BASE_URL}/public-search?${params.toString()}`, {
    headers: { Accept: "application/json" }
  });

  if (!response.ok) throw new Error(`Polymarket API ${response.status}`);
  const payload = await response.json();
  const markets = flattenMarkets(payload).filter(isWinnerMarket);

  if (!markets.length) {
    throw new Error("No World Cup winner markets found in Polymarket response");
  }

  state.polymarket.lastMarkets = markets;
  state.polymarket.lastEventCount = (payload.events || []).length;
  return markets;
}

function setupFilters() {
  const groups = [...new Set(state.data.teams.map((team) => team.group))].sort();
  els.groupFilter.innerHTML = '<option value="all">全部</option>';
  groups.forEach((group) => {
    const option = document.createElement("option");
    option.value = group;
    option.textContent = `小组 ${group}`;
    els.groupFilter.appendChild(option);
  });

  els.searchInput.addEventListener("input", (event) => {
    state.query = event.target.value.trim();
    render();
  });

  els.groupFilter.addEventListener("change", (event) => {
    state.group = event.target.value;
    render();
  });

  els.sortSelect.addEventListener("change", (event) => {
    state.sort = event.target.value;
    render();
  });

  document.querySelectorAll("[data-history-view]").forEach((button) => {
    button.addEventListener("click", () => {
      state.historyView = button.dataset.historyView;
      document.querySelectorAll("[data-history-view]").forEach((tab) => tab.classList.remove("active"));
      button.classList.add("active");
      renderHistory();
    });
  });

  els.refreshButton.addEventListener("click", refreshData);
}

function shortAddress(address) {
  return address ? `${address.slice(0, 5)}...${address.slice(-4)}` : "";
}

function setWalletMessage(message) {
  els.walletMessage.textContent = message;
}

function setAccessMessage(message) {
  els.accessMessage.textContent = message;
}

function setAccessStep(step) {
  document.querySelectorAll("[data-access-step]").forEach((item) => {
    item.classList.toggle("active", item.dataset.accessStep === step);
  });
}

function setWalletMenu(open) {
  els.walletMenu.hidden = !open;
  if (open) setWalletMessage("");
}

function renderWalletState() {
  const connected = Boolean(walletState.address);
  els.walletButtonText.textContent = connected ? shortAddress(walletState.address) : "Connect Wallet";
  els.walletOptions.hidden = connected;
  els.walletConnected.hidden = !connected;
  els.walletConnectedLabel.textContent = connected
    ? `${walletState.name} · ${shortAddress(walletState.address)}`
    : "";
}

function buildSolanaPayUrl() {
  if (!SOLANA_USDC_RECIPIENT) return "";
  const params = new URLSearchParams({
    amount: PREMIUM_PRICE_USDC,
    "spl-token": SOLANA_USDC_MINT,
    label: "FIFA 2026 Premium",
    message: "Permanent premium access"
  });
  return `solana:${SOLANA_USDC_RECIPIENT}?${params.toString()}`;
}

function renderAccessPayment() {
  if (!walletState.address) return;
  els.accessWalletOptions.hidden = true;
  els.accessPayment.hidden = false;
  els.accessWalletAddress.textContent = shortAddress(walletState.address);
  setAccessStep("payment");

  const payUrl = buildSolanaPayUrl();
  if (!payUrl) {
    els.accessPayButton.classList.add("disabled");
    els.accessPayButton.removeAttribute("href");
    setAccessMessage("收款地址尚未配置。请先在 app.js 中设置 SOLANA_USDC_RECIPIENT。");
    return;
  }

  els.accessPayButton.classList.remove("disabled");
  els.accessPayButton.href = payUrl;
  setAccessMessage("钱包已连接。付款完成后会自动检查到账状态。");
  startPaymentPolling();
}

function solanaAddress(result, provider) {
  return result?.publicKey?.toString?.() || provider?.publicKey?.toString?.() || "";
}

async function connectPhantom() {
  const provider = window.phantom?.solana;
  if (!provider?.isPhantom) {
    setWalletMessage("未检测到 Phantom 扩展，请先安装后重试。");
    return;
  }
  const result = await provider.connect();
  walletState.provider = provider;
  walletState.address = solanaAddress(result, provider);
  walletState.name = "Phantom";
}

async function connectOkxSolana() {
  const provider = window.okxwallet?.solana;
  if (!provider) {
    setWalletMessage("未检测到 OKX Wallet 扩展，请先安装或使用移动端 WalletConnect。");
    return;
  }
  const result = await provider.connect();
  walletState.provider = provider;
  walletState.address = solanaAddress(result, provider);
  walletState.name = "OKX Wallet · Solana";
}

async function connectWallet(wallet) {
  setWalletMessage("正在连接钱包...");
  try {
    if (wallet === "phantom") await connectPhantom();
    if (wallet === "okx-solana") await connectOkxSolana();

    if (walletState.address) {
      renderWalletState();
      setWalletMessage("钱包已连接。");
      renderAccessPayment();
    }
  } catch (error) {
    console.warn(error);
    setWalletMessage("连接已取消或失败，请重试。");
  }
}

async function checkPremiumAccess() {
  if (!walletState.address) {
    setAccessMessage("请先连接钱包。");
    return;
  }
  if (!SOLANA_USDC_RECIPIENT) {
    setAccessMessage("收款地址尚未配置，暂时不能验证支付。");
    return;
  }
  setAccessStep("verify");
  setAccessMessage("正在检查链上到账...");
  els.accessCheckButton.disabled = true;

  try {
    const response = await fetch("/api/payments/status-solana", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        walletAddress: walletState.address
      })
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || "支付状态检查失败。");
    }
    if (!payload.success) {
      setAccessMessage("暂未检测到到账。付款完成后系统会继续自动检查。");
      setAccessStep("payment");
      return;
    }

    localStorage.setItem(ACCESS_UNLOCK_KEY, payload.developerMode ? "developer" : "true");
    if (payload.developerMode) {
      setAccessMessage("开发者模式已启用。");
    }
    stopPaymentPolling();
    els.accessGate.hidden = true;
  } catch (error) {
    console.warn(error);
    setAccessMessage(error.message || "支付状态检查失败，请稍后重试。");
    setAccessStep("payment");
  } finally {
    els.accessCheckButton.disabled = false;
  }
}

function stopPaymentPolling() {
  if (!walletState.paymentPoll) return;
  clearInterval(walletState.paymentPoll);
  walletState.paymentPoll = null;
}

function startPaymentPolling() {
  stopPaymentPolling();
  walletState.paymentPoll = setInterval(checkPremiumAccess, 6000);
}

async function disconnectWallet() {
  stopPaymentPolling();
  try {
    if (walletState.provider?.disconnect) await walletState.provider.disconnect();
  } catch (error) {
    console.warn(error);
  }
  walletState.provider = null;
  walletState.address = "";
  walletState.name = "";
  renderWalletState();
  setWalletMessage("钱包已断开。");
}

function setupWallet() {
  els.walletButton.addEventListener("click", () => setWalletMenu(els.walletMenu.hidden));
  els.walletCloseButton.addEventListener("click", () => setWalletMenu(false));
  els.walletDisconnectButton.addEventListener("click", disconnectWallet);
  els.walletOptions.addEventListener("click", (event) => {
    const button = event.target.closest("[data-wallet]");
    if (button) connectWallet(button.dataset.wallet);
  });
  els.accessWalletOptions.addEventListener("click", (event) => {
    const button = event.target.closest("[data-access-wallet]");
    if (button) connectWallet(button.dataset.accessWallet);
  });
  els.accessCheckButton.addEventListener("click", checkPremiumAccess);
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".wallet-control")) setWalletMenu(false);
  });
  if (localStorage.getItem(ACCESS_UNLOCK_KEY) === "true") {
    els.accessGate.hidden = true;
  }
  renderWalletState();
}

function filteredTeams() {
  return state.data.teams
    .filter((team) => state.group === "all" || team.group === state.group)
    .filter((team) => matchQuery(team, state.query))
    .sort((a, b) => {
      if (state.sort === "name") return a.name.localeCompare(b.name);
      if (state.sort === "group") return a.group.localeCompare(b.group) || b.probability - a.probability;
      return b.probability - a.probability;
    });
}

function renderContenders() {
  const teams = filteredTeams().slice(0, 14);
  els.contendersList.innerHTML = teams
    .map((team, index) => {
      const width = Math.max(2, Math.min(100, team.probability * 5.5));
      return `
        <div class="contender">
          <span class="rank">${index + 1}</span>
          <div class="team-name">
            <strong>${team.name}</strong>
            <span>${team.code} · ${team.confederation} · ${team.form}</span>
          </div>
          <div class="bar" aria-label="${team.name} 夺冠胜率 ${team.probability}%"><span style="width:${width}%"></span></div>
          <span class="probability">${team.probability.toFixed(1)}%</span>
        </div>
      `;
    })
    .join("");
}

function renderTeams() {
  const teams = filteredTeams();
  els.teamGrid.innerHTML = teams
    .map((team) => `
      <article class="team-card">
        <div class="team-name">
          <a class="team-detail-link" href="./team.html?team=${encodeURIComponent(team.code)}">
            <strong>${team.name}</strong>
          </a>
          <span>${team.code} · 小组 ${team.group}</span>
        </div>
        <div class="team-meta">
          <span>${team.confederation}</span>
          <span>${team.probability.toFixed(1)}%</span>
          <span>${team.form}</span>
        </div>
        ${team.marketUrl ? `
          <a class="market-link" href="${team.marketUrl}" target="_blank" rel="noreferrer">
            查看 Polymarket 市场
          </a>
        ` : ""}
        <div class="players">
          ${team.players.map((player) => `
            <div class="player-card">
              <strong>${player.name}</strong>
              <span>${player.position} · ${player.club}</span>
            </div>
          `).join("")}
        </div>
      </article>
    `)
    .join("");
}

function renderMvp() {
  els.mvpList.innerHTML = state.data.mvpCandidates
    .filter((player) => matchQuery(player, state.query))
    .sort((a, b) => b.rating - a.rating)
    .map((player) => `
      <article class="mvp-card">
        <div class="mvp-top">
          <div class="team-name">
            <strong>${player.name}</strong>
            <span>${player.team} · ${player.position}</span>
          </div>
          <span class="tag">${player.rating.toFixed(1)}</span>
        </div>
        <p class="hint">${player.reason}</p>
      </article>
    `)
    .join("");
}

function renderBracketTeam(team) {
  const score = team.score === null ? "-" : team.score;
  return `
    <div class="bracket-team ${team.state}">
      <span>${team.name}</span>
      <strong>${score}</strong>
    </div>
  `;
}

function renderBracket() {
  const bracket = window.WORLD_CUP_BRACKET;
  if (!bracket || !els.bracketGrid) return;

  els.bracketUpdatedAt.textContent = bracket.source === "demo"
    ? "赛程演示 · 等待赛果 API"
    : `更新：${formatDate(bracket.updatedAt)}`;

  els.bracketGrid.innerHTML = bracket.rounds.map((round) => `
    <section class="bracket-round">
      <h4>${round.name}</h4>
      <div class="bracket-matches">
        ${round.matches.map((match) => `
          <article class="bracket-match ${match.status}">
            <div class="bracket-match-meta">
              <span>${match.date}</span>
              <strong>${match.status === "live" ? `LIVE ${match.minute || ""}` : match.id}</strong>
            </div>
            ${match.teams.map(renderBracketTeam).join("")}
          </article>
        `).join("")}
      </div>
    </section>
  `).join("");
}

function renderHistory() {
  if (state.historyView === "players") {
    els.historyContent.innerHTML = `
      <div class="player-table">
        ${state.data.historicalPlayers
          .filter((player) => matchQuery(player, state.query))
          .map((player) => `
            <div class="player-row">
              <strong>${player.name}</strong>
              <span>${player.team}</span>
              <span>${player.role}</span>
              <span>${player.years} · ${player.note}</span>
            </div>
          `).join("")}
      </div>
    `;
    return;
  }

  els.historyContent.innerHTML = `
    <div class="history-grid">
      ${state.data.historicalEditions
        .filter((edition) => matchQuery(edition, state.query))
        .sort((a, b) => b.year - a.year)
        .map((edition) => `
          <article class="edition-card">
            <h4>${edition.year} · ${edition.host}</h4>
            <p><strong>冠军：</strong>${edition.champion}</p>
            <p><strong>亚军：</strong>${edition.runnerUp}</p>
            <p><strong>队伍：</strong>${edition.teams}</p>
            <p>${edition.notableSquads}</p>
          </article>
        `).join("")}
    </div>
  `;
}

function renderMeta() {
  els.updatedAt.textContent = `更新：${formatDate(state.data.meta.updatedAt)}`;
  els.editionCount.textContent = state.data.historicalEditions.length;
}

function render() {
  renderMeta();
  renderContenders();
  renderMvp();
  renderBracket();
  renderTeams();
  renderHistory();
}

function setRefreshLabel(text) {
  els.refreshState.textContent = text;
}

async function refreshData() {
  setRefreshLabel("正在更新实时数据...");
  try {
    const markets = await fetchPolymarketMarkets();
    const matched = applyPolymarketMarkets(markets);
    setRefreshLabel(`实时数据 · 已更新 ${matched} 队`);
    render();
  } catch (error) {
    console.warn(error);
    state.data.meta = {
      ...state.data.meta,
      updatedAt: new Date().toISOString(),
      status: "demo",
      note: `Polymarket 同步失败：${error.message}`
    };
    setRefreshLabel("实时数据失败 · 使用本地数据");
    render();
  }
}

setupFilters();
setupWallet();
render();
refreshData();
setInterval(refreshData, 30000);
