const POLYMARKET_BASE_URL = "https://gamma-api.polymarket.com";
const DEFAULT_POLYMARKET_QUERY = "2026 world cup winner";

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
  updatedAt: document.querySelector("#updatedAt"),
  refreshButton: document.querySelector("#refreshButton"),
  refreshState: document.querySelector("#refreshState"),
  editionCount: document.querySelector("#editionCount"),
  apiForm: document.querySelector("#apiForm"),
  apiUrl: document.querySelector("#apiUrl"),
  apiToken: document.querySelector("#apiToken")
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
  els.apiUrl.value = state.polymarket.query;
  els.apiToken.value = POLYMARKET_BASE_URL;
  els.apiForm.addEventListener("submit", connectPolymarket);
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
          <strong>${team.name}</strong>
          <span>${team.code} · 小组 ${team.group}</span>
        </div>
        <div class="team-meta">
          <span>${team.confederation}</span>
          <span>${team.probability.toFixed(1)}%</span>
          <span>${team.form}</span>
        </div>
        ${team.marketSource ? `
          <a class="market-link" href="${team.marketUrl || "https://polymarket.com"}" target="_blank" rel="noreferrer">
            ${team.marketSource}
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
  renderTeams();
  renderHistory();
}

function setRefreshLabel(text) {
  els.refreshState.textContent = text;
}

async function refreshData() {
  setRefreshLabel("正在同步 Polymarket...");
  try {
    const markets = await fetchPolymarketMarkets();
    const matched = applyPolymarketMarkets(markets);
    setRefreshLabel(`Polymarket 实时 · 匹配 ${matched} 队`);
    render();
  } catch (error) {
    console.warn(error);
    state.data.meta = {
      ...state.data.meta,
      updatedAt: new Date().toISOString(),
      status: "demo",
      note: `Polymarket 同步失败：${error.message}`
    };
    setRefreshLabel("Polymarket 失败 · 使用本地数据");
    render();
  }
}

async function connectPolymarket(event) {
  event.preventDefault();
  state.polymarket.query = els.apiUrl.value.trim() || DEFAULT_POLYMARKET_QUERY;
  localStorage.setItem("wcPolymarketQuery", state.polymarket.query);
  await refreshData();
}

setupFilters();
render();
refreshData();
setInterval(refreshData, 30000);
