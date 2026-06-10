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
  if (!team) return '<span class="flag-fallback">待</span>';
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
  els.updatedAt.textContent = `Updated: ${formatDate(state.data.meta.updatedAt)}`;
  els.editionCount.textContent = state.data.historicalEditions.length;
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
  els.teamGrid.innerHTML = filteredTeams().map((team) => `
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
}

function buildGroupSchedule() {
  const pairings = [
    { matchday: 1, label: "第 1 轮", pairs: [[0, 1], [2, 3]] },
    { matchday: 2, label: "第 2 轮", pairs: [[0, 2], [3, 1]] },
    { matchday: 3, label: "第 3 轮", pairs: [[3, 0], [1, 2]] }
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
          score: "等待开赛",
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
      ${calendar.map((item) => `
        <article class="schedule-day">
          <div class="schedule-cell matchup"><span>对战组</span><strong>${teamLabel(item.home)} <b>vs</b> ${teamLabel(item.away)}</strong></div>
          <div class="schedule-cell"><span>时间</span><time>${escapeHtml(item.bjt)}</time></div>
          <div class="schedule-cell"><span>小组赛组别</span><strong>${escapeHtml(item.group)} · ${escapeHtml(item.label)}</strong></div>
          <div class="schedule-cell venue"><span>比赛地点</span><strong>${escapeHtml(item.venue)}</strong></div>
          <div class="schedule-score"><span>比分窗口</span><strong>${escapeHtml(item.score)}</strong></div>
        </article>
      `).join("")}
    </div>
  `;
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
    { roundId: "quarter", roundName: "1/4决赛", matches: [
      { id: "qf1", time: "等待开赛", team1: pick("BRA"), team2: pick("ESP") },
      { id: "qf2", time: "等待开赛", team1: pick("ARG"), team2: pick("NED") },
      { id: "qf3", time: "等待开赛", team1: pick("FRA"), team2: pick("ENG") },
      { id: "qf4", time: "等待开赛", team1: pick("POR"), team2: pick("MAR") }
    ] },
    { roundId: "semi", roundName: "半决赛", matches: [
      { id: "sf1", time: "等待晋级球队", team1: null, team2: null },
      { id: "sf2", time: "等待晋级球队", team1: null, team2: null }
    ] },
    { roundId: "final", roundName: "决赛", matches: [
      { id: "final", time: "等待晋级球队", team1: null, team2: null }
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
  const query = state.query;
  const tabs = document.querySelectorAll("[data-history-view]");
  tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.historyView === state.historyView));

  if (state.historyView === "players") {
    const players = state.data.historicalPlayers.filter((player) => matchQuery(player, query));
    els.historyContent.innerHTML = `
      <div class="player-grid">
        ${players.map((player) => `
          <article class="player-card">
            <span class="tag">${escapeHtml(player.year)}</span>
            <h4>${escapeHtml(player.name)}</h4>
            <p>${escapeHtml(player.country)} - ${escapeHtml(player.position)}</p>
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
            <h4>${escapeHtml(edition.winner)} champion</h4>
            <p>${escapeHtml(edition.final)} - ${escapeHtml(edition.score)}</p>
          </div>
          <div class="player-row">
            ${edition.standouts.map((player) => `<span>${escapeHtml(player)}</span>`).join("")}
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
  void refreshLiveFootball();
  void refreshSportsNews();
  if (state.syncStarted) return;
  state.syncStarted = true;
  setInterval(refreshData, 15_000);
  setInterval(refreshLiveFootball, 15_000);
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
  renderHistory();
}

setupFilters();
render();
startDataSync();
