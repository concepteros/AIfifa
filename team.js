const COACHES = {
  ARG: { name: "Lionel Scaloni", nationality: "Argentina", since: "2018" },
  BRA: { name: "Carlo Ancelotti", nationality: "Italy", since: "2025" },
  ENG: { name: "Thomas Tuchel", nationality: "Germany", since: "2025" },
  ESP: { name: "Luis de la Fuente", nationality: "Spain", since: "2022" },
  FRA: { name: "Didier Deschamps", nationality: "France", since: "2012" },
  GER: { name: "Julian Nagelsmann", nationality: "Germany", since: "2023" },
  JPN: { name: "Hajime Moriyasu", nationality: "Japan", since: "2018" },
  MEX: { name: "Javier Aguirre", nationality: "Mexico", since: "2024" },
  NED: { name: "Ronald Koeman", nationality: "Netherlands", since: "2023" },
  POR: { name: "Roberto Martinez", nationality: "Spain", since: "2023" },
  USA: { name: "Mauricio Pochettino", nationality: "Argentina", since: "2024" }
};

const NEWS = {
  ARG: [
    { date: "2026-05-30", title: "卫冕冠军公布赛前训练安排", summary: "球队将围绕高强度恢复和定位球演练完成最后阶段准备。" },
    { date: "2026-05-27", title: "阿根廷确认核心框架保持稳定", summary: "教练组延续成熟体系，同时为年轻球员保留轮换空间。" }
  ],
  BRA: [
    { date: "2026-05-31", title: "巴西强化前场组合演练", summary: "训练重点放在边路推进和禁区前沿的小范围配合。" },
    { date: "2026-05-28", title: "教练组强调攻守转换效率", summary: "球队希望减少丢球后的暴露空间，提高回防速度。" }
  ],
  FRA: [
    { date: "2026-05-31", title: "法国队完成一堂高强度训练课", summary: "锋线与中场重点演练快速推进和二点球控制。" },
    { date: "2026-05-29", title: "法国队继续保持深度轮换策略", summary: "教练组将根据对手特点灵活调整首发结构。" }
  ],
  ESP: [
    { date: "2026-05-30", title: "西班牙继续打磨控球体系", summary: "球队训练集中在高位压迫和快速转移球。" }
  ]
};

function coachFor(team) {
  return COACHES[team.code] || {
    name: "官方信息待更新",
    nationality: team.name,
    since: "TBD"
  };
}

function newsFor(team) {
  return NEWS[team.code] || [
    {
      date: "2026-06-01",
      title: `${team.name} 进入世界杯备战阶段`,
      summary: "球队最新动态将在接入新闻数据 API 后实时更新。"
    },
    {
      date: "2026-05-29",
      title: "最终名单与训练计划持续更新",
      summary: "球员出场状态和伤病信息将在官方公告后同步。"
    }
  ];
}

function renderNotFound() {
  document.querySelector("#teamDetail").innerHTML = `
    <section class="panel detail-empty">
      <p class="eyebrow">Not Found</p>
      <h2>没有找到这支球队。</h2>
      <a class="back-link" href="./">返回球队列表</a>
    </section>
  `;
}

function renderTeam(team) {
  const coach = coachFor(team);
  const updates = newsFor(team);
  document.title = `${team.name} · 世界杯数据中心`;
  document.querySelector("#teamDetail").innerHTML = `
    <section class="detail-hero">
      <div>
        <p class="eyebrow">${team.code} · Group ${team.group} · ${team.confederation}</p>
        <h2>${team.name}</h2>
        <p>${team.form} · 本届夺冠隐含胜率 ${team.probability.toFixed(1)}%</p>
      </div>
      <div class="detail-odds">
        <span>夺冠胜率</span>
        <strong>${team.probability.toFixed(1)}%</strong>
      </div>
    </section>

    <section class="detail-layout">
      <article class="panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Squad</p>
            <h3>球员信息</h3>
          </div>
          <span>${team.players.length} 名已录入球员</span>
        </div>
        <div class="detail-player-list">
          ${team.players.map((player, index) => `
            <div class="detail-player-row">
              <span class="player-number">${String(index + 1).padStart(2, "0")}</span>
              <strong>${player.name}</strong>
              <span>${player.position}</span>
              <span>${player.club}</span>
            </div>
          `).join("")}
        </div>
      </article>

      <aside>
        <article class="panel coach-panel">
          <p class="eyebrow">Head Coach</p>
          <h3>${coach.name}</h3>
          <p>${coach.nationality} · 执教起始 ${coach.since}</p>
        </article>

        <article class="panel">
          <p class="eyebrow">Team Profile</p>
          <div class="profile-list">
            <div><span>代码</span><strong>${team.code}</strong></div>
            <div><span>赛区</span><strong>${team.confederation}</strong></div>
            <div><span>小组</span><strong>${team.group}</strong></div>
            <div><span>风格</span><strong>${team.form}</strong></div>
          </div>
        </article>
      </aside>
    </section>

    <section class="panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Latest Updates</p>
          <h3>球队最新动态</h3>
        </div>
      </div>
      <div class="news-list">
        ${updates.map((update) => `
          <article class="news-item">
            <time datetime="${update.date}">${update.date}</time>
            <div>
              <h4>${update.title}</h4>
              <p>${update.summary}</p>
            </div>
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

const code = new URLSearchParams(window.location.search).get("team");
const team = window.WORLD_CUP_DATA.teams.find((item) => item.code === code);

if (team) renderTeam(team);
else renderNotFound();
