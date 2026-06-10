const state = {
  data: structuredClone(window.WORLD_CUP_DATA),
  query: "",
  group: "all",
  sort: "probability",
  historyView: "editions",
  syncStarted: false
};

const GROUP_SCHEDULE_META = {
  1: {
    A: { date: "2026-06-12", time: "03:00", venues: ["Estadio Azteca, Mexico City", "Estadio Guadalajara"] },
    B: { date: "2026-06-13", time: "06:00", venues: ["BMO Field, Toronto", "BC Place, Vancouver"] },
    C: { date: "2026-06-14", time: "03:00", venues: ["Hard Rock Stadium, Miami", "Mercedes-Benz Stadium, Atlanta"] },
    D: { date: "2026-06-13", time: "10:00", venues: ["SoFi Stadium, Los Angeles", "Levi's Stadium, San Francisco Bay Area"] },
    E: { date: "2026-06-15", time: "03:00", venues: ["AT&T Stadium, Dallas", "NRG Stadium, Houston"] },
    F: { date: "2026-06-15", time: "06:00", venues: ["Lumen Field, Seattle", "BC Place, Vancouver"] },
    G: { date: "2026-06-16", time: "03:00", venues: ["MetLife Stadium, New York New Jersey", "Lincoln Financial Field, Philadelphia"] },
    H: { date: "2026-06-16", time: "06:00", venues: ["Gillette Stadium, Boston", "Hard Rock Stadium, Miami"] },
    I: { date: "2026-06-17", time: "03:00", venues: ["Arrowhead Stadium, Kansas City", "AT&T Stadium, Dallas"] },
    J: { date: "2026-06-17", time: "06:00", venues: ["Mercedes-Benz Stadium, Atlanta", "NRG Stadium, Houston"] },
    K: { date: "2026-06-18", time: "03:00", venues: ["Estadio Monterrey", "Estadio Guadalajara"] },
    L: { date: "2026-06-18", time: "06:00", venues: ["SoFi Stadium, Los Angeles", "Levi's Stadium, San Francisco Bay Area"] }
  },
  2: {
    A: { date: "2026-06-19", time: "03:00", venues: ["Estadio Azteca, Mexico City", "Estadio Monterrey"] },
    B: { date: "2026-06-19", time: "06:00", venues: ["BMO Field, Toronto", "BC Place, Vancouver"] },
    C: { date: "2026-06-20", time: "03:00", venues: ["Hard Rock Stadium, Miami", "Mercedes-Benz Stadium, Atlanta"] },
    D: { date: "2026-06-20", time: "06:00", venues: ["SoFi Stadium, Los Angeles", "Lumen Field, Seattle"] },
    E: { date: "2026-06-21", time: "03:00", venues: ["AT&T Stadium, Dallas", "NRG Stadium, Houston"] },
    F: { date: "2026-06-21", time: "06:00", venues: ["Levi's Stadium, San Francisco Bay Area", "BC Place, Vancouver"] },
    G: { date: "2026-06-22", time: "03:00", venues: ["MetLife Stadium, New York New Jersey", "Lincoln Financial Field, Philadelphia"] },
    H: { date: "2026-06-22", time: "06:00", venues: ["Gillette Stadium, Boston", "Hard Rock Stadium, Miami"] },
    I: { date: "2026-06-23", time: "03:00", venues: ["Arrowhead Stadium, Kansas City", "AT&T Stadium, Dallas"] },
    J: { date: "2026-06-23", time: "06:00", venues: ["Mercedes-Benz Stadium, Atlanta", "NRG Stadium, Houston"] },
    K: { date: "2026-06-24", time: "03:00", venues: ["Estadio Monterrey", "Estadio Guadalajara"] },
    L: { date: "2026-06-24", time: "06:00", venues: ["SoFi Stadium, Los Angeles", "Levi's Stadium, San Francisco Bay Area"] }
  },
  3: {
    A: { date: "2026-06-25", time: "03:00", venues: ["Estadio Azteca, Mexico City", "Estadio Guadalajara"] },
    B: { date: "2026-06-25", time: "06:00", venues: ["BMO Field, Toronto", "BC Place, Vancouver"] },
    C: { date: "2026-06-25", time: "10:00", venues: ["Hard Rock Stadium, Miami", "Mercedes-Benz Stadium, Atlanta"] },
    D: { date: "2026-06-26", time: "03:00", venues: ["SoFi Stadium, Los Angeles", "Lumen Field, Seattle"] },
    E: { date: "2026-06-26", time: "06:00", venues: ["AT&T Stadium, Dallas", "NRG Stadium, Houston"] },
    F: { date: "2026-06-26", time: "10:00", venues: ["Levi's Stadium, San Francisco Bay Area", "BC Place, Vancouver"] },
    G: { date: "2026-06-27", time: "03:00", venues: ["MetLife Stadium, New York New Jersey", "Lincoln Financial Field, Philadelphia"] },
    H: { date: "2026-06-27", time: "06:00", venues: ["Gillette Stadium, Boston", "Hard Rock Stadium, Miami"] },
    I: { date: "2026-06-27", time: "10:00", venues: ["Arrowhead Stadium, Kansas City", "AT&T Stadium, Dallas"] },
    J: { date: "2026-06-28", time: "03:00", venues: ["Mercedes-Benz Stadium, Atlanta", "NRG Stadium, Houston"] },
    K: { date: "2026-06-28", time: "06:00", venues: ["Estadio Monterrey", "Estadio Guadalajara"] },
    L: { date: "2026-06-28", time: "10:00", venues: ["SoFi Stadium, Los Angeles", "Levi's Stadium, San Francisco Bay Area"] }
  }
};

const els = {
  searchInput: document.querySelector("#searchInput"),
  groupFilter: document.querySelector("#groupFilter"),
  sortSelect: document.querySelector("#sortSelect"),
  contendersList: document.querySelector("#contendersList"),
  teamGrid: document.querySelector("#teamGrid"),
  watchGuideCalendar: document.querySelector("#watchGuideCalendar"),
  groupOddsList: document.querySelector("#groupOddsList"),
  groupOddsUpdatedAt: document.querySelector("#groupOddsUpdatedAt"),
  knockoutBracket: document.querySelector("#knockoutBracket"),
  mvpList: document.querySelector("#mvpList"),
  historyContent: document.querySelector("#historyContent"),
  liveMatchList: document.querySelector("#liveMatchList"),
  standingsList: document.querySelector("#standingsList"),
  footballUpdatedAt: document.querySelector("#footballUpdatedAt"),
  sportsNewsList: document.querySelector("#sportsNewsList"),
  sportsNewsUpdatedAt: document.querySelector("#sportsNewsUpdatedAt"),
  updatedAt: document.querySelector("#updatedAt"),
  refreshButton: document.querySelector("#refreshButton"),
  refreshState: document.querySelector("#refreshState"),
  editionCount: document.querySelector("#editionCount")
};

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  })[character]);
}

function formatDate(value) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

function flagMarkup(team, className = "team-flag") {
  if (!team) return '<span class="flag-fallback">\u5f85</span>';
  if (team.flag) {
    return `<img class="${className}" src="${escapeHtml(team.flag)}" alt="${escapeHtml(team.name)} flag" loading="lazy" referrerpolicy="no-referrer" onerror="this.replaceWith(document.createTextNode('${escapeHtml(team.flagEmoji || "")}'))" />`;
  }
  return `<span class="flag-emoji" aria-hidden="true">${escapeHtml(team.flagEmoji || "")}</span>`;
}

function teamLabel(team) {
  if (!team) return "TBD";
  return `${team.flagEmoji ? `${team.flagEmoji} ` : ""}${team.name}`;
}

function teamByCode(code) {
  return state.data.teams.find((team) => team.code === code);
}

function normalize(value) {
  return String(value || "").toLowerCase();
}

function matchQuery(item, query) {
  if (!query) return true;
  const text = [
    item.name,
    item.team,
    item.country,
    item.code,
    item.position,
    item.club,
    item.year,
    item.players?.map((player) => `${player.name} ${player.club}`).join(" ")
  ].filter(Boolean).join(" ");
  return normalize(text).includes(normalize(query));
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

function setRefreshLabel(text) {
  if (els.refreshState) els.refreshState.textContent = text;
}

function renderMeta() {
  if (els.updatedAt) els.updatedAt.textContent = `Updated: ${formatDate(state.data.meta.updatedAt)}`;
  if (els.editionCount) els.editionCount.textContent = state.data.historicalEditions.length;
}

function renderContenders() {
  const max = Math.max(...state.data.teams.map((team) => team.probability));
  els.contendersList.innerHTML = filteredTeams().slice(0, 16).map((team, index) => {
    const width = Math.max(6, (team.probability / max) * 100);
    return `
      <div class="contender">
        <span class="rank">${index + 1}</span>
        <div class="team-name">
          <strong>${flagMarkup(team)}<span>${escapeHtml(team.name)}</span></strong>
          <span>${escapeHtml(team.code)} - ${escapeHtml(team.confederation)} - ${escapeHtml(team.form)}</span>
        </div>
        <div class="bar" aria-label="${escapeHtml(team.name)} win probability ${team.probability}%"><span style="width:${width}%"></span></div>
        <span class="probability">${team.probability.toFixed(1)}%</span>
      </div>
    `;
  }).join("");
}

function renderTeams() {
  const teams = filteredTeams();
  const visibleCount = window.matchMedia("(max-width: 760px)").matches ? 4 : 8;
  const visibleTeams = teams.slice(0, visibleCount);
  const collapsedTeams = teams.slice(visibleCount);
  const renderTeamCards = (items) => items.map((team) => `
    <article class="team-card">
      <div class="team-name">
        <a class="team-detail-link" href="./team.html?team=${encodeURIComponent(team.code)}">
          <strong class="team-title">
            ${flagMarkup(team)}
            <span>${escapeHtml(team.name)}</span>
          </strong>
        </a>
        <span>${escapeHtml(team.code)} - Group ${escapeHtml(team.group)}</span>
      </div>
      <div class="team-meta">
        <span>${escapeHtml(team.confederation)}</span>
        <span>${team.probability.toFixed(1)}%</span>
        <span>${escapeHtml(team.form)}</span>
      </div>
      <a class="squad-link" href="./team.html?team=${encodeURIComponent(team.code)}">
        View full ${window.WORLD_CUP_SQUADS?.[team.code]?.length || team.players.length} player squad
      </a>
    </article>
  `).join("");

  els.teamGrid.innerHTML = `
    <div class="team-grid-visible">
      ${renderTeamCards(visibleTeams)}
    </div>
    ${collapsedTeams.length ? `
      <details class="team-grid-more">
        <summary>展开其余 ${collapsedTeams.length} 支球队</summary>
        <div class="team-grid-more-list">
          ${renderTeamCards(collapsedTeams)}
        </div>
      </details>
    ` : ""}
  `;
}

function buildGroupSchedule() {
  const pairings = [
    { matchday: 1, label: "\u7b2c 1 \u8f6e", pairs: [[0, 1], [2, 3]] },
    { matchday: 2, label: "\u7b2c 2 \u8f6e", pairs: [[0, 2], [3, 1]] },
    { matchday: 3, label: "\u7b2c 3 \u8f6e", pairs: [[3, 0], [1, 2]] }
  ];
  const groups = state.data.teams.reduce((result, team) => {
    (result[team.group] ||= []).push(team);
    return result;
  }, {});

  const meta = GROUP_SCHEDULE_META;
  return pairings.flatMap((round) => (
    Object.entries(groups).flatMap(([group, teams]) => (
      round.pairs.map(([homeIndex, awayIndex], pairIndex) => {
        const matchMeta = meta[round.matchday]?.[group] || {};
        return {
          bjt: `${matchMeta.date || "TBD"} ${matchMeta.time || "TBD"} BJT`,
          group,
          label: round.label,
          venue: matchMeta.venues?.[pairIndex] || "Venue TBD",
          score: "\u7b49\u5f85\u5f00\u8d5b",
          home: teams[homeIndex],
          away: teams[awayIndex]
        };
      })
    ))
  ));
}

function renderWatchGuide() {
  if (!els.watchGuideCalendar) return;
  const highlights = [
    { date: "2026-06-12 03:00 BJT", stage: "Opening match", title: `${teamLabel(teamByCode("MEX"))} vs ${teamLabel(teamByCode("RSA"))}`, detail: "Estadio Azteca, Mexico City" },
    { date: "2026-06-13 06:00 BJT", stage: "Host debut", title: `${teamLabel(teamByCode("CAN"))} vs ${teamLabel(teamByCode("BIH"))}`, detail: "BMO Field, Toronto" },
    { date: "2026-06-13 10:00 BJT", stage: "Host debut", title: `${teamLabel(teamByCode("USA"))} vs ${teamLabel(teamByCode("PAR"))}`, detail: "SoFi Stadium, Los Angeles" },
    { date: "2026-07-20 03:00 BJT", stage: "Final", title: "World Cup Final", detail: "MetLife Stadium, New York New Jersey" }
  ];
  const calendar = buildGroupSchedule();
  const firstDay = calendar[0]?.bjt?.split(" ")[0] || "";
  const firstDayMatches = calendar.filter((item) => item.bjt.startsWith(firstDay));
  const laterMatches = calendar.filter((item) => !item.bjt.startsWith(firstDay));
  const renderScheduleItems = (items) => items.map((item) => `
    <article class="schedule-day">
      <div class="schedule-cell matchup"><span>\u5bf9\u6218\u7ec4</span><strong>${teamLabel(item.home)} <b>vs</b> ${teamLabel(item.away)}</strong></div>
      <div class="schedule-cell"><span>\u65f6\u95f4</span><time>${escapeHtml(item.bjt)}</time></div>
      <div class="schedule-cell"><span>\u5c0f\u7ec4\u8d5b\u7ec4\u522b</span><strong>${escapeHtml(item.group)} \u7ec4 ${escapeHtml(item.label)}</strong></div>
      <div class="schedule-cell venue"><span>\u6bd4\u8d5b\u5730\u70b9</span><strong>${escapeHtml(item.venue)}</strong></div>
      <div class="schedule-score"><span>\u6bd4\u5206\u7a97\u53e3</span><strong>${escapeHtml(item.score)}</strong></div>
    </article>
  `).join("");

  els.watchGuideCalendar.innerHTML = `
    <div class="watch-highlights">
      ${highlights.map((item) => `
        <article class="watch-highlight">
          <span>${escapeHtml(item.date)}</span>
          <strong>${escapeHtml(item.title)}</strong>
          <small>${escapeHtml(item.stage)}</small>
          <p>${escapeHtml(item.detail)}</p>
        </article>
      `).join("")}
    </div>
    <div class="schedule-calendar">
      <div class="schedule-day-group">
        <div class="schedule-day-heading">
          <strong>\u7b2c\u4e00\u5929\u8d5b\u7a0b</strong>
          <span>${escapeHtml(firstDay)} \u5171 ${firstDayMatches.length} \u573a</span>
        </div>
        ${renderScheduleItems(firstDayMatches)}
      </div>
      <details class="schedule-more">
        <summary>\u5c55\u5f00\u540e\u7eed\u5c0f\u7ec4\u8d5b\u8d5b\u7a0b ${laterMatches.length} \u573a</summary>
        <div class="schedule-more-list">
          ${renderScheduleItems(laterMatches)}
        </div>
      </details>
    </div>
  `;
}

const TEAM_MARKET_ALIASES = {
  BIH: ["bosnia", "bosnia and herzegovina"],
  CAN: ["can", "canada"],
  CIV: ["cote d ivoire", "ivory coast"],
  COD: ["congo dr", "dr congo", "democratic republic of congo"],
  CZE: ["czechia", "czech republic"],
  ENG: ["england"],
  IRN: ["iran", "ir iran"],
  KOR: ["korea republic", "south korea", "kr"],
  MEX: ["mexico"],
  NED: ["netherlands", "holland"],
  RSA: ["south africa"],
  SCO: ["scotland"],
  SUI: ["switzerland", "che"],
  USA: ["united states", "usa", "usmnt"],
};

function normalizeMarketName(value) {
  return String(value || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function teamMarketAliases(team) {
  if (!team) return [];
  return [...new Set([
    team.name,
    team.code,
    ...(TEAM_MARKET_ALIASES[team.code] || [])
  ].map(normalizeMarketName).filter(Boolean))];
}

function marketContainsTeam(market, team) {
  const aliases = teamMarketAliases(team);
  const text = normalizeMarketName([
    market.question,
    market.slug,
    market.outcomes?.map((outcome) => outcome.name).join(" ")
  ].filter(Boolean).join(" "));
  return aliases.some((alias) => text.includes(alias));
}

function outcomeForTeam(market, team) {
  const aliases = teamMarketAliases(team);
  return market.outcomes?.find((outcome) => {
    const outcomeName = normalizeMarketName(outcome.name);
    return aliases.some((alias) => outcomeName === alias || outcomeName.includes(alias));
  }) || null;
}

function drawOutcome(market) {
  return market.outcomes?.find((outcome) => normalizeMarketName(outcome.name) === "draw") || null;
}

function formatMarketPrice(value) {
  const price = typeof value === "number" ? value : value?.price;
  if (!Number.isFinite(price) || price <= 0) return "暂无";
  return `${(price * 100).toFixed(1)}%`;
}

const PREDICT_TEAM_SLUGS = {
  KOR: "kr",
  POR: "prt",
  SUI: "che",
};

function predictTeamSlug(team) {
  return (PREDICT_TEAM_SLUGS[team?.code] || team?.code || "").toLowerCase();
}

function predictMatchDate(match) {
  const [date, time] = String(match.bjt || "").split(" ");
  if (!date || !time || date === "TBD" || time === "TBD") return "";
  const value = new Date(`${date}T${time}:00+08:00`);
  return Number.isNaN(value.getTime()) ? "" : value.toISOString().slice(0, 10);
}

function predictMatchKeys(match) {
  const home = predictTeamSlug(match.home);
  const away = predictTeamSlug(match.away);
  const date = predictMatchDate(match);
  if (!home || !away || !date) return [];
  return [
    `fifwc-${home}-${away}-${date}`,
    `fifwc-${away}-${home}-${date}`,
  ];
}

function findMatchMarkets(markets, match) {
  const keys = predictMatchKeys(match);
  return (markets || []).filter((market) => keys.includes(market.categorySlug));
}

function findPredictOutcome(markets, team, kind = "win") {
  const aliases = teamMarketAliases(team);
  return markets.find((market) => {
    const text = normalizeMarketName(`${market.title} ${market.question}`);
    if (kind === "draw") return text.includes("draw");
    return text.includes("win") && aliases.some((alias) => text.includes(alias));
  }) || null;
}

function currentScheduleDay() {
  const calendar = buildGroupSchedule();
  const firstDay = calendar[0]?.bjt?.split(" ")[0] || "";
  return calendar.filter((item) => item.bjt.startsWith(firstDay));
}

function renderGroupOdds(payload) {
  if (!els.groupOddsList) return;
  const matches = currentScheduleDay();
  const markets = payload.markets || [];
  els.groupOddsUpdatedAt.textContent = payload.stale
    ? `最近快照：${formatDate(payload.updatedAt)}`
    : `60 秒轮询 · ${formatDate(payload.updatedAt)}`;

  els.groupOddsList.innerHTML = matches.map((match) => {
    const matchMarkets = findMatchMarkets(markets, match);
    const home = findPredictOutcome(matchMarkets, match.home);
    const away = findPredictOutcome(matchMarkets, match.away);
    const draw = findPredictOutcome(matchMarkets, null, "draw");
    const market = home || away || draw || matchMarkets[0] || null;
    return `
      <article class="group-odds-card ${market ? "" : "is-empty"}">
        <div class="group-odds-match">
          <span>${escapeHtml(match.bjt)} · ${escapeHtml(match.group)} 组</span>
          <strong>${teamLabel(match.home)} <b>vs</b> ${teamLabel(match.away)}</strong>
          <small>${escapeHtml(match.venue)}</small>
        </div>
        <div class="group-odds-prices">
          <span><small>${escapeHtml(match.home.name)}</small><strong>${formatMarketPrice(home)}</strong></span>
          <span><small>平局</small><strong>${formatMarketPrice(draw)}</strong></span>
          <span><small>${escapeHtml(match.away.name)}</small><strong>${formatMarketPrice(away)}</strong></span>
        </div>
        <div class="group-odds-source">
          ${market
            ? `<a href="${escapeHtml(market.url)}" target="_blank" rel="noreferrer">Predict.fun · ${escapeHtml(matchMarkets.length)} 个相关盘口</a>`
            : "<span>当前赛程暂无可匹配 Predict.fun 盘口</span>"}
        </div>
      </article>
    `;
  }).join("");
}

async function refreshGroupOdds() {
  if (!els.groupOddsList) return;
  try {
    const response = await fetch("/api/predict/group-odds", { headers: { Accept: "application/json" } });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Predict.fun 盘口加载失败");
    renderGroupOdds(payload);
  } catch (error) {
    console.warn(error);
    els.groupOddsUpdatedAt.textContent = "盘口暂时不可用";
    renderGroupOdds({
      markets: [],
      stale: true,
      updatedAt: new Date().toISOString(),
    });
  }
}

function renderMvp() {
  els.mvpList.innerHTML = state.data.mvpCandidates
    .filter((player) => matchQuery(player, state.query))
    .sort((a, b) => b.rating - a.rating)
    .map((player) => `
      <article class="mvp-card">
        <div class="mvp-top">
          <div class="team-name">
            <strong>${escapeHtml(player.name)}</strong>
            <span>${escapeHtml(player.team)} - ${escapeHtml(player.position)}</span>
          </div>
          <span class="tag">${player.rating.toFixed(1)}</span>
        </div>
        <p class="hint">${escapeHtml(player.reason)}</p>
      </article>
    `).join("");
}

function buildKnockoutBracket() {
  const pick = (code) => teamByCode(code) || null;
  return [
    { roundId: "quarter", roundName: "1/4\u51b3\u8d5b", matches: [
      { id: "qf1", time: "\u7b49\u5f85\u5f00\u8d5b", team1: pick("BRA"), team2: pick("ESP") },
      { id: "qf2", time: "\u7b49\u5f85\u5f00\u8d5b", team1: pick("ARG"), team2: pick("NED") },
      { id: "qf3", time: "\u7b49\u5f85\u5f00\u8d5b", team1: pick("FRA"), team2: pick("ENG") },
      { id: "qf4", time: "\u7b49\u5f85\u5f00\u8d5b", team1: pick("POR"), team2: pick("MAR") }
    ] },
    { roundId: "semi", roundName: "\u534a\u51b3\u8d5b", matches: [
      { id: "sf1", time: "\u7b49\u5f85\u664b\u7ea7\u7403\u961f", team1: null, team2: null },
      { id: "sf2", time: "\u7b49\u5f85\u664b\u7ea7\u7403\u961f", team1: null, team2: null }
    ] },
    { roundId: "final", roundName: "\u51b3\u8d5b", matches: [
      { id: "final", time: "\u7b49\u5f85\u664b\u7ea7\u7403\u961f", team1: null, team2: null }
    ] }
  ];
}

function renderBracketTeam(team) {
  return `
    <div class="team-info">
      ${team ? flagMarkup(team, "team-flag") : '<span class="flag-fallback">待</span>'}
      <span>${team ? escapeHtml(team.name) : "TBD"}</span>
    </div>
    <div class="score">-</div>
  `;
}

function renderKnockoutBracket() {
  if (!els.knockoutBracket) return;
  els.knockoutBracket.innerHTML = buildKnockoutBracket().map((round) => `
    <div class="round round-${round.roundId}">
      <div class="round-title">${escapeHtml(round.roundName)}</div>
      ${round.matches.map((match) => `
        <article class="match-box" data-match-id="${escapeHtml(match.id)}">
          <div class="match-status">${escapeHtml(match.time)}</div>
          <div class="team-row">${renderBracketTeam(match.team1)}</div>
          <div class="team-row">${renderBracketTeam(match.team2)}</div>
        </article>
      `).join("")}
    </div>
  `).join("");
}

function renderHistory() {
  if (!els.historyContent) return;
  const query = state.query;
  const tabs = document.querySelectorAll("[data-history-view]");
  tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.historyView === state.historyView));

  if (state.historyView === "players") {
    const players = state.data.historicalPlayers.filter((player) => matchQuery(player, query));
    els.historyContent.innerHTML = `
      <div class="player-grid">
        ${players.map((player) => `
          <article class="player-card">
            <span class="tag">${escapeHtml(player.year || player.years || "")}</span>
            <h4>${escapeHtml(player.name)}</h4>
            <p>${escapeHtml(player.country || player.team || "")} - ${escapeHtml(player.position || player.role || "")}</p>
            <small>${escapeHtml(player.note)}</small>
          </article>
        `).join("")}
      </div>
    `;
    return;
  }

  const editions = state.data.historicalEditions.filter((edition) => matchQuery(edition, query));
  els.historyContent.innerHTML = `
    <div class="edition-list">
      ${editions.map((edition) => `
        <article class="edition-card">
          <div>
            <p class="eyebrow">${escapeHtml(edition.year)} - ${escapeHtml(edition.host)}</p>
            <h4>${escapeHtml(edition.winner || edition.champion)} champion</h4>
            <p>${escapeHtml(edition.final || `${edition.champion || ""} vs ${edition.runnerUp || ""}`)}${edition.score ? ` - ${escapeHtml(edition.score)}` : ""}</p>
          </div>
          <div class="player-row">
            ${(edition.standouts || String(edition.notableSquads || "").split(";")).filter(Boolean).map((player) => `<span>${escapeHtml(player)}</span>`).join("")}
          </div>
        </article>
      `).join("")}
    </div>
  `;
}

function normalizeTeamName(value) {
  return String(value || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function findTeamByName(name) {
  const target = normalizeTeamName(name);
  return state.data.teams.find((team) => (
    normalizeTeamName(team.name) === target ||
    normalizeTeamName(team.code) === target ||
    normalizeTeamName(team.sourceName) === target
  ));
}

function matchTeamLabel(name) {
  const team = findTeamByName(name);
  return team ? teamLabel(team) : name;
}

function renderEvents(events = []) {
  if (!events.length) return '<p class="live-empty-detail">暂无关键事件</p>';
  return `
    <div class="live-events">
      ${events.slice(-5).reverse().map((event) => `
        <div>
          <strong>${event.time ?? "-"}'</strong>
          <span>${escapeHtml(event.team)} - ${escapeHtml(event.type)}${event.detail ? ` - ${escapeHtml(event.detail)}` : ""}</span>
          <small>${escapeHtml(event.player || "")}</small>
        </div>
      `).join("")}
    </div>
  `;
}

function renderLiveFootball(payload) {
  if (!els.liveMatchList || !els.standingsList) return;
  els.footballUpdatedAt.textContent = payload.configured
    ? `更新：${formatDate(payload.updatedAt)}`
    : "等待开赛";

  if (!payload.liveMatches.length) {
    els.liveMatchList.innerHTML = `
      <div class="live-empty">
        <strong>等待开赛</strong>
        <span>比赛开始后将每 15 秒自动刷新比分和关键事件。</span>
      </div>
    `;
  } else {
    els.liveMatchList.innerHTML = payload.liveMatches.map((match) => `
      <article class="live-match-card">
        <div class="live-match-meta">
          <span class="live-badge">${escapeHtml(match.status)} - ${match.elapsed ?? "-"}'</span>
          <span>${escapeHtml(match.round)}${match.venue ? ` - ${escapeHtml(match.venue)}` : ""}</span>
        </div>
        <div class="live-score">
          <div><strong>${escapeHtml(matchTeamLabel(match.home.name))}</strong><span>主队</span></div>
          <b>${match.home.score ?? 0} - ${match.away.score ?? 0}</b>
          <div><strong>${escapeHtml(matchTeamLabel(match.away.name))}</strong><span>客队</span></div>
        </div>
        ${renderEvents(match.events)}
      </article>
    `).join("");
  }

  els.standingsList.innerHTML = payload.standings.length
    ? payload.standings.map((group) => `
      <div class="standing-group">
        <strong>${escapeHtml(group.group)}</strong>
        ${group.teams.map((team) => `
          <div class="standing-row">
            <span>${escapeHtml(matchTeamLabel(team.name))}</span>
            <b>${team.points}</b>
          </div>
        `).join("")}
      </div>
    `).join("")
    : '<p class="live-empty-detail">等待开赛</p>';
}

async function refreshLiveFootball() {
  if (!els.liveMatchList || !els.standingsList) return;
  try {
    const response = await fetch("/api/football/live-matches", { headers: { Accept: "application/json" } });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "赛事数据请求失败");
    renderLiveFootball(payload);
  } catch (error) {
    console.warn(error);
    renderLiveFootball({
      configured: false,
      liveMatches: [],
      standings: [],
      updatedAt: new Date().toISOString()
    });
  }
}

function renderSportsNews(payload) {
  if (!els.sportsNewsList) return;
  els.sportsNewsUpdatedAt.textContent = payload.stale ? "最近快照" : `更新：${formatDate(payload.updatedAt)}`;
  els.sportsNewsList.innerHTML = payload.articles.length
    ? payload.articles.map((article) => `
      <article class="sports-news-card">
        ${article.imageUrl ? `<img src="${escapeHtml(article.imageUrl)}" alt="" loading="lazy" referrerpolicy="no-referrer" />` : ""}
        <div>
          <span>${escapeHtml(article.source || "Sports News")}</span>
          <h4><a href="${escapeHtml(article.link)}" target="_blank" rel="noreferrer">${escapeHtml(article.title)}</a></h4>
          ${article.publishedAt ? `<time>${escapeHtml(formatDate(article.publishedAt))}</time>` : ""}
        </div>
      </article>
    `).join("")
    : '<p class="live-empty-detail">暂无体育新闻。</p>';
}

async function refreshSportsNews() {
  try {
    const response = await fetch("/api/news/sports", { headers: { Accept: "application/json" } });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "体育新闻加载失败");
    renderSportsNews(payload);
  } catch (error) {
    console.warn(error);
    els.sportsNewsUpdatedAt.textContent = "暂不可用";
    els.sportsNewsList.innerHTML = '<p class="live-empty-detail">体育新闻暂时不可用。</p>';
  }
}

function refreshData() {
  state.data.meta = {
    ...state.data.meta,
    updatedAt: new Date().toISOString(),
    status: "local",
    note: "使用本地球队数据"
  };
  setRefreshLabel("本地数据已更新");
  render();
}

function startDataSync() {
  void refreshData();
  if (els.liveMatchList && els.standingsList) void refreshLiveFootball();
  void refreshGroupOdds();
  void refreshSportsNews();
  if (state.syncStarted) return;
  state.syncStarted = true;
  setInterval(refreshData, 15_000);
  if (els.liveMatchList && els.standingsList) setInterval(refreshLiveFootball, 15_000);
  setInterval(refreshGroupOdds, 60_000);
  setInterval(refreshSportsNews, 10 * 60_000);
}

function populateGroups() {
  const groups = [...new Set(state.data.teams.map((team) => team.group))].sort();
  els.groupFilter.innerHTML = '<option value="all">全部</option>' +
    groups.map((group) => `<option value="${escapeHtml(group)}">Group ${escapeHtml(group)}</option>`).join("");
}

function setupFilters() {
  populateGroups();
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
      renderHistory();
    });
  });
  els.refreshButton.addEventListener("click", refreshData);
}

function render() {
  renderMeta();
  renderContenders();
  renderWatchGuide();
  renderKnockoutBracket();
  renderMvp();
  renderTeams();
  if (els.historyContent) renderHistory();
}

setupFilters();
render();
startDataSync();
