const page = document.body.dataset.portalPage;
const POLL_INTERVAL_MS = 15_000;
const PREDICTION_POLL_INTERVAL_MS = 10_000;
let fallbackVoterId = "";

const MVP_WINNERS = [
  { year: 1978, name: "Mario Kempes", team: "Argentina" },
  { year: 1982, name: "Paolo Rossi", team: "Italy" },
  { year: 1986, name: "Diego Maradona", team: "Argentina" },
  { year: 1990, name: "Salvatore Schillaci", team: "Italy" },
  { year: 1994, name: "Romario", team: "Brazil" },
  { year: 1998, name: "Ronaldo", team: "Brazil" },
  { year: 2002, name: "Oliver Kahn", team: "Germany" },
  { year: 2006, name: "Zinedine Zidane", team: "France" },
  { year: 2010, name: "Diego Forlan", team: "Uruguay" },
  { year: 2014, name: "Lionel Messi", team: "Argentina" },
  { year: 2018, name: "Luka Modric", team: "Croatia" },
  { year: 2022, name: "Lionel Messi", team: "Argentina" }
];

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

function formatDate(value) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

function normalizeTeamName(value) {
  return String(value || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function teamLabel(team) {
  if (!team) return "TBD";
  return `${team.flagEmoji ? `${team.flagEmoji} ` : ""}${team.name}`;
}

function findTeamByName(name) {
  const target = normalizeTeamName(name);
  return window.WORLD_CUP_DATA.teams.find((team) => (
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
          <span>${event.team} · ${event.type}${event.detail ? ` · ${event.detail}` : ""}</span>
          <small>${event.player || ""}</small>
        </div>
      `).join("")}
    </div>
  `;
}

function renderLiveMatches(payload) {
  const list = document.querySelector("#portalLiveMatches");
  const updatedAt = document.querySelector("#portalFootballUpdatedAt");
  if (!list || !updatedAt) return;

  updatedAt.textContent = payload.configured
    ? `更新：${formatDate(payload.updatedAt)}`
    : "等待开赛";

  if (!payload.liveMatches.length) {
    list.innerHTML = `
      <div class="live-empty">
        <strong>等待开赛</strong>
        <span>比赛开始后将每 15 秒自动刷新比分和关键事件。</span>
      </div>
    `;
    return;
  }

  list.innerHTML = payload.liveMatches.map((match) => `
    <article class="live-match-card">
      <div class="live-match-meta">
        <span class="live-badge">${match.status} · ${match.elapsed ?? "-"}'</span>
        <span>${match.round}${match.venue ? ` · ${match.venue}` : ""}</span>
      </div>
      <div class="live-score">
        <div><strong>${matchTeamLabel(match.home.name)}</strong><span>主队</span></div>
        <b>${match.home.score ?? 0} - ${match.away.score ?? 0}</b>
        <div><strong>${matchTeamLabel(match.away.name)}</strong><span>客队</span></div>
      </div>
      ${renderEvents(match.events)}
    </article>
  `).join("");
}

async function refreshLiveMatches() {
  try {
    const response = await fetch("/api/football/live-matches", {
      headers: { Accept: "application/json" }
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "赛事数据请求失败");
    renderLiveMatches(payload);
  } catch (error) {
    console.warn(error);
    renderLiveMatches({
      configured: false,
      liveMatches: [],
      updatedAt: new Date().toISOString()
    });
  }
}

function groupedTeams() {
  return window.WORLD_CUP_DATA.teams.reduce((result, team) => {
    (result[team.group] ||= []).push(team);
    return result;
  }, {});
}

function renderGroups() {
  const target = document.querySelector("#portalGroups");
  if (!target) return;
  target.innerHTML = Object.entries(groupedTeams()).map(([group, teams]) => `
    <article class="portal-group">
      <h3>小组 ${group}</h3>
      ${teams.map((team) => `
        <a href="./team.html?team=${encodeURIComponent(team.code)}">
          <strong class="team-title">
            <span class="flag-emoji" aria-hidden="true">${team.flagEmoji || ""}</span>
            <span>${team.name}</span>
          </strong>
          <span>${team.code}</span>
        </a>
      `).join("")}
    </article>
  `).join("");
}

function buildGroupSchedule() {
  const pairings = [
    { matchday: 1, label: "第 1 轮", pairs: [[0, 1], [2, 3]] },
    { matchday: 2, label: "第 2 轮", pairs: [[0, 2], [3, 1]] },
    { matchday: 3, label: "第 3 轮", pairs: [[3, 0], [1, 2]] }
  ];
  const groups = groupedTeams();

  return pairings.flatMap((round) => (
    Object.entries(groups).flatMap(([group, teams]) => (
      round.pairs.map(([homeIndex, awayIndex], pairIndex) => {
        const meta = GROUP_SCHEDULE_META[round.matchday]?.[group] || {};
        return {
          date: meta.date || "TBD",
          time: meta.time || "TBD",
          bjt: `${meta.date || "TBD"} ${meta.time || "TBD"} BJT`,
          matchday: round.label,
          group,
          venue: meta.venues?.[pairIndex] || "Venue TBD",
          score: "等待开赛",
          home: teams[homeIndex],
          away: teams[awayIndex]
        };
      })
    ))
  ));
}

function renderGroupSchedule() {
  const target = document.querySelector("#portalGroupSchedule");
  if (!target) return;
  const grouped = buildGroupSchedule().reduce((result, match) => {
    (result[match.date] ||= []).push(match);
    return result;
  }, {});

  target.innerHTML = Object.entries(grouped).map(([date, items]) => `
    <section class="group-schedule-day">
      <div class="group-schedule-date">
        <time>${date} BJT</time>
        <span>${items.length} 场比赛</span>
      </div>
      <div class="group-schedule-matches">
        ${items.map((match) => `
          <article class="group-schedule-match">
            <div class="schedule-cell matchup">
              <span>对战组</span>
              <strong>${teamLabel(match.home)} <b>vs</b> ${teamLabel(match.away)}</strong>
            </div>
            <div class="schedule-cell">
              <span>时间</span>
              <time>${match.bjt}</time>
            </div>
            <div class="schedule-cell">
              <span>小组赛组别</span>
              <strong>${match.group} · ${match.matchday}</strong>
            </div>
            <div class="schedule-cell venue">
              <span>比赛地点</span>
              <strong>${match.venue}</strong>
            </div>
            <div class="schedule-score">
              <span>比分窗口</span>
              <strong>${match.score}</strong>
            </div>
          </article>
        `).join("")}
      </div>
    </section>
  `).join("");
}

function renderMvpHistory() {
  const target = document.querySelector("#portalMvpGrid");
  if (!target) return;
  target.innerHTML = [...MVP_WINNERS].reverse().map((winner) => `
    <article class="portal-mvp-card">
      <span>${winner.year}</span>
      <div>
        <h3>${winner.name}</h3>
        <p>${winner.team}</p>
      </div>
    </article>
  `).join("");
}

function getVoterId() {
  try {
    const existing = localStorage.getItem("fifa2026VoterId");
    if (existing) return existing;
  } catch {}

  if (fallbackVoterId) return fallbackVoterId;
  const voterId = crypto.randomUUID?.() || `vote-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  fallbackVoterId = voterId;
  try {
    localStorage.setItem("fifa2026VoterId", voterId);
  } catch {}
  return voterId;
}

function renderPredictionResults(payload) {
  const teamNames = new Map(window.WORLD_CUP_DATA.teams.map((team) => [team.code, teamLabel(team)]));
  const currentName = teamNames.get(payload.currentTeamCode);
  const current = document.querySelector("#predictionCurrent");
  const submitButton = document.querySelector("#predictionSubmitButton");

  current.textContent = `你的预测：${currentName || "尚未提交"}`;
  submitButton.textContent = currentName ? "修改预测" : "提交预测";
  if (payload.currentTeamCode) {
    document.querySelector("#predictionTeam").value = payload.currentTeamCode;
  }
  document.querySelector("#predictionTotal").textContent = `${payload.total} 票`;
  document.querySelector("#predictionResults").innerHTML = payload.results.length
    ? payload.results.map((result) => `
      <div class="prediction-result">
        <div>
          <strong>${teamNames.get(result.teamCode) || result.teamCode}</strong>
          <span>${result.votes} 票 · ${result.percentage.toFixed(1)}%</span>
        </div>
        <div class="bar"><span style="width:${result.percentage}%"></span></div>
      </div>
    `).join("")
    : '<p class="live-empty-detail">还没有投票，提交第一份预测吧。</p>';
}

async function refreshPredictions() {
  const voterId = encodeURIComponent(getVoterId());
  const response = await fetch(`/api/predictions?voterId=${voterId}`, {
    headers: { Accept: "application/json" }
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "投票结果加载失败");
  renderPredictionResults(payload);
}

async function submitPrediction(event) {
  event.preventDefault();
  const message = document.querySelector("#predictionMessage");
  const teamCode = document.querySelector("#predictionTeam").value;
  message.textContent = "正在提交预测...";

  try {
    const response = await fetch("/api/predictions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ teamCode, voterId: getVoterId() })
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "预测提交失败");
    renderPredictionResults(payload);
    message.textContent = "预测已记录，你可以随时修改选择。";
  } catch (error) {
    message.textContent = error.message;
  }
}

function setupPredictions() {
  const teams = [...window.WORLD_CUP_DATA.teams].sort((a, b) => a.name.localeCompare(b.name));
  document.querySelector("#predictionTeam").innerHTML = teams.map((team) => `
    <option value="${team.code}">${teamLabel(team)} · ${team.code}</option>
  `).join("");
  document.querySelector("#predictionForm").addEventListener("submit", submitPrediction);
  refreshPredictions().catch((error) => {
    document.querySelector("#predictionMessage").textContent = error.message;
  });
  setInterval(() => {
    refreshPredictions().catch(() => {});
  }, PREDICTION_POLL_INTERVAL_MS);
}

if (page === "groups") {
  renderGroups();
  renderGroupSchedule();
  refreshLiveMatches();
  setInterval(refreshLiveMatches, POLL_INTERVAL_MS);
}

if (page === "mvp") {
  renderMvpHistory();
}

if (page === "predictions") {
  setupPredictions();
}
