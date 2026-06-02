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

function formatDate(value) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

function renderEvents(events) {
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
        <div><strong>${match.home.name}</strong><span>主队</span></div>
        <b>${match.home.score ?? 0} - ${match.away.score ?? 0}</b>
        <div><strong>${match.away.name}</strong><span>客队</span></div>
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

function renderGroups() {
  const target = document.querySelector("#portalGroups");
  const groups = window.WORLD_CUP_DATA.teams.reduce((result, team) => {
    (result[team.group] ||= []).push(team);
    return result;
  }, {});
  target.innerHTML = Object.entries(groups).map(([group, teams]) => `
    <article class="portal-group">
      <h3>小组 ${group}</h3>
      ${teams.map((team) => `
        <a href="./team.html?team=${encodeURIComponent(team.code)}">
          <strong class="team-title">
            ${team.flag ? `<img class="team-flag" src="${team.flag}" alt="" />` : ""}
            <span>${team.name}</span>
          </strong>
          <span>${team.code}</span>
        </a>
      `).join("")}
    </article>
  `).join("");
}

function renderBracketTeam(team) {
  return `
    <div class="bracket-team ${team.state}">
      <span>${team.name}</span>
      <strong>${team.score ?? "-"}</strong>
    </div>
  `;
}

function renderBracket() {
  const bracket = window.WORLD_CUP_BRACKET;
  document.querySelector("#portalBracketUpdatedAt").textContent = `更新：${formatDate(bracket.updatedAt)}`;
  document.querySelector("#portalBracketGrid").innerHTML = bracket.rounds.map((round) => `
    <section class="bracket-round">
      <h4>${round.name}</h4>
      <div class="bracket-matches">
        ${round.matches.map((match) => `
          <article class="bracket-match ${match.status}">
            <div class="bracket-match-meta">
              <span>${match.date}</span>
              <strong>${match.status === "live" ? match.minute : match.status}</strong>
            </div>
            ${match.teams.map(renderBracketTeam).join("")}
          </article>
        `).join("")}
      </div>
    </section>
  `).join("");
}

function renderMvpHistory() {
  document.querySelector("#portalMvpGrid").innerHTML = [...MVP_WINNERS].reverse().map((winner) => `
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
  const teamNames = new Map(window.WORLD_CUP_DATA.teams.map((team) => [team.code, team.name]));
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
    <option value="${team.code}">${team.name} · ${team.code}</option>
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
  refreshLiveMatches();
  setInterval(refreshLiveMatches, POLL_INTERVAL_MS);
}

if (page === "mvp") {
  renderMvpHistory();
}

if (page === "predictions") {
  setupPredictions();
}
