import { createExecutorClient } from "../services/executor-client.js";

const client = createExecutorClient();
let activePanel = "strategy";
let latestStatus = null;

const panelTitles = {
  strategy: "策略",
  monitor: "监控",
  copyTrading: "跟单",
  scraper: "刮刀",
  profit: "收益"
};

const panelMetrics = {
  strategy: [
    ["启用策略", (status) => status.panels.strategy.enabled],
    ["观察策略", (status) => status.panels.strategy.observing],
    ["交易策略", (status) => status.panels.strategy.trading]
  ],
  monitor: [
    ["待处理信号", (status) => status.panels.monitor.pendingSignals],
    ["警告", (status) => status.panels.monitor.warnings],
    ["错误", (status) => status.panels.monitor.errors]
  ],
  copyTrading: [
    ["目标地址", (status) => status.panels.copyTrading.targetAddresses],
    ["启用地址", (status) => status.panels.copyTrading.enabledTargets],
    ["单笔上限", (status) => `${status.risk.maxOrderUsd} USDC`]
  ],
  scraper: [
    ["刮刀规则", (status) => status.panels.scraper.rules],
    ["运行规则", (status) => status.panels.scraper.activeRules],
    ["候选项", (status) => status.panels.scraper.candidates]
  ],
  profit: [
    ["交易数", (status) => status.panels.profit.trades],
    ["已实现", (status) => `${status.panels.profit.realizedPnlUsd} USDC`],
    ["未实现估算", (status) => `${status.panels.profit.estimatedUnrealizedPnlUsd} USDC`]
  ]
};

function renderPanel(status) {
  document.querySelector("#panelTitle").textContent = panelTitles[activePanel];
  document.querySelector("#panelContent").innerHTML = panelMetrics[activePanel].map(([label, read]) => `
    <article class="metric-card">
      <p class="eyebrow">${label}</p>
      <strong>${read(status)}</strong>
    </article>
  `).join("");
}

function renderStatus(status) {
  latestStatus = status;
  const banner = document.querySelector("#statusBanner");
  const paused = status.risk.emergencyPaused;
  document.querySelector("#connectionLabel").textContent = "Connected";
  document.querySelector("#pauseButton").textContent = paused ? "解除暂停" : "紧急暂停";
  banner.classList.toggle("is-paused", paused);
  banner.textContent = paused
    ? "自动交易已紧急暂停。"
    : `本地执行器已连接，Polymarket ${status.platforms.polymarket.mode}，Predict.fun ${status.platforms.predictfun.mode}。`;
  renderPanel(status);
}

function renderDisconnected(error) {
  latestStatus = null;
  document.querySelector("#connectionLabel").textContent = "Disconnected";
  document.querySelector("#statusBanner").textContent = `无法连接本地执行器：${error.message}`;
  document.querySelector("#panelContent").innerHTML = "";
}

async function refreshStatus() {
  try {
    renderStatus(await client.getStatus());
  } catch (error) {
    renderDisconnected(error);
  }
}

document.querySelectorAll("[data-panel]").forEach((button) => {
  button.addEventListener("click", () => {
    activePanel = button.dataset.panel;
    document.querySelectorAll("[data-panel]").forEach((item) => {
      item.classList.toggle("is-active", item === button);
    });
    if (latestStatus) renderPanel(latestStatus);
  });
});

document.querySelector("#pauseButton").addEventListener("click", async () => {
  if (!latestStatus) return;
  try {
    renderStatus(await client.setEmergencyPause(!latestStatus.risk.emergencyPaused));
  } catch (error) {
    renderDisconnected(error);
  }
});

refreshStatus();
setInterval(refreshStatus, 5000);
