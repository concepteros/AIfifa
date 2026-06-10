const SOLANA_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v";
const SOLANA_USDC_RECIPIENT = "EwAh2VbsbgG2xWsFsDYMjmCUqq48cSkms1HATZDi3Vgq";
const PREMIUM_PRICE_UNITS = 19_900_000n;
const SOLANA_RPC_URL = "https://mainnet.helius-rpc.com/?api-key=46b445f1-d996-4af0-97a9-e41cd82aef93";
const FRONTEND_ACCESS_KEY = "fifa2026PremiumAccess";
const FRONTEND_ACCESS_COOKIE = "fifa2026_frontend_access";
const FRONTEND_ACCESS_MAX_AGE = 365 * 24 * 60 * 60;
const DEVELOPER_WALLETS = new Set([SOLANA_USDC_RECIPIENT]);
const TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA";
const ASSOCIATED_TOKEN_PROGRAM_ID = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL";
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
  historyView: "editions"
};

const els = {
  searchInput: document.querySelector("#searchInput"),
  groupFilter: document.querySelector("#groupFilter"),
  sortSelect: document.querySelector("#sortSelect"),
  contendersList: document.querySelector("#contendersList"),
  teamGrid: document.querySelector("#teamGrid"),
  watchGuideCalendar: document.querySelector("#watchGuideCalendar"),
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
  accountChangedHandler: null,
  accountsChangedHandler: null,
  paymentCheckInFlight: false,
  paymentPoll: null
};

const accessState = {
  syncStarted: false,
  unlocked: false
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
  return [team.name, team.code, team.sourceName, ...(TEAM_ALIASES[team.name] || [])].map(normalize);
}

function teamMentioned(text, team) {
  const source = ` ${normalize(text)} `;
  return aliasesFor(team).some((alias) => alias && source.includes(` ${alias} `));
}

function findTeamByName(name) {
  const target = normalize(name);
  return state.data.teams.find((team) => aliasesFor(team).some((alias) => alias === target));
}

function teamLabel(team) {
  if (!team) return "TBD";
  return `${team.flagEmoji ? `${team.flagEmoji} ` : ""}${team.name}`;
}

function matchTeamLabel(name) {
  const team = findTeamByName(name);
  return team ? teamLabel(team) : name;
}

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

function groupedTeams() {
  return state.data.teams.reduce((result, team) => {
    (result[team.group] ||= []).push(team);
    return result;
  }, {});
}

function buildGroupSchedule() {
  const rounds = [
    { matchday: 1, label: "MD1", pairs: [[0, 1], [2, 3]] },
    { matchday: 2, label: "MD2", pairs: [[0, 2], [3, 1]] },
    { matchday: 3, label: "MD3", pairs: [[3, 0], [1, 2]] }
  ];
  const groups = groupedTeams();
  return rounds.flatMap((round) => (
    Object.entries(groups).flatMap(([group, teams]) => (
      round.pairs.map(([homeIndex, awayIndex], pairIndex) => {
        const meta = GROUP_SCHEDULE_META[round.matchday]?.[group] || {};
        return {
          date: meta.date || "TBD",
          time: meta.time || "TBD",
          bjt: `${meta.date || "TBD"} ${meta.time || "TBD"} BJT`,
          label: round.label,
          group,
          venue: meta.venues?.[pairIndex] || "Venue TBD",
          score: "Waiting",
          home: teams[homeIndex],
          away: teams[awayIndex]
        };
      })
    ))
  ));
}

function teamByCode(code) {
  return state.data.teams.find((team) => team.code === code);
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

function renderAccessPayment() {
  if (!walletState.address) return;
  if (DEVELOPER_WALLETS.has(walletState.address)) {
    grantFrontendAccess(walletState.address);
    unlockAccess("开发者模式已启用。");
    return;
  }
  els.accessWalletOptions.hidden = true;
  els.accessPayment.hidden = false;
  els.accessWalletAddress.textContent = shortAddress(walletState.address);
  setAccessStep("payment");

  if (!SOLANA_USDC_RECIPIENT) {
    els.accessPayButton.classList.add("disabled");
    els.accessPayButton.disabled = true;
    setAccessMessage("收款地址尚未配置。请先在 app.js 中设置 SOLANA_USDC_RECIPIENT。");
    return;
  }

  els.accessPayButton.classList.remove("disabled");
  els.accessPayButton.disabled = false;
  setAccessMessage("钱包已连接。付款完成后会自动检查到账状态。");
  startPaymentPolling();
  void checkPremiumAccess();
}

function startPremiumDataSync() {
  void refreshData();
  void refreshLiveFootball();
  void refreshSportsNews();
  if (accessState.syncStarted) return;
  accessState.syncStarted = true;
  setInterval(refreshData, 15000);
  setInterval(refreshLiveFootball, 15000);
  setInterval(refreshSportsNews, 10 * 60 * 1000);
}

function unlockAccess(message = "") {
  accessState.unlocked = true;
  stopPaymentPolling();
  els.accessGate.hidden = true;
  if (message) setAccessMessage(message);
  startPremiumDataSync();
}

function accessCookieValue(walletAddress) {
  return encodeURIComponent(`${walletAddress}:${Date.now()}`);
}

function grantFrontendAccess(walletAddress) {
  const payload = {
    grantedAt: new Date().toISOString(),
    walletAddress
  };
  try {
    localStorage.setItem(FRONTEND_ACCESS_KEY, JSON.stringify(payload));
  } catch {
    // Cookie access still allows the server-hosted pages to load.
  }
  const secure = location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${FRONTEND_ACCESS_COOKIE}=${accessCookieValue(walletAddress)}; Path=/; Max-Age=${FRONTEND_ACCESS_MAX_AGE}; SameSite=Strict${secure}`;
}

function clearFrontendAccess() {
  try {
    localStorage.removeItem(FRONTEND_ACCESS_KEY);
  } catch {}
  document.cookie = `${FRONTEND_ACCESS_COOKIE}=; Path=/; Max-Age=0; SameSite=Strict`;
}

function storedFrontendAccess() {
  try {
    const payload = JSON.parse(localStorage.getItem(FRONTEND_ACCESS_KEY) || "null");
    return payload?.walletAddress ? payload : null;
  } catch {
    return null;
  }
}

function lockAccessGate(message = "请连接已解锁钱包，或连接钱包完成支付。") {
  accessState.unlocked = false;
  stopPaymentPolling();
  els.accessGate.hidden = false;
  els.accessWalletOptions.hidden = false;
  els.accessPayment.hidden = true;
  setAccessStep("wallet");
  setAccessMessage(message);
}

function associatedTokenAddress(owner, mint) {
  const { PublicKey } = window.solanaWeb3;
  const tokenProgram = new PublicKey(TOKEN_PROGRAM_ID);
  const associatedTokenProgram = new PublicKey(ASSOCIATED_TOKEN_PROGRAM_ID);
  return PublicKey.findProgramAddressSync(
    [owner.toBuffer(), tokenProgram.toBuffer(), mint.toBuffer()],
    associatedTokenProgram
  )[0];
}

function u64Bytes(value) {
  const bytes = new Uint8Array(8);
  let remaining = BigInt(value);
  for (let index = 0; index < bytes.length; index += 1) {
    bytes[index] = Number(remaining & 255n);
    remaining >>= 8n;
  }
  return bytes;
}

function createRecipientAtaInstruction(payer, recipient, mint, recipientAta) {
  const { PublicKey, SystemProgram, TransactionInstruction } = window.solanaWeb3;
  return new TransactionInstruction({
    programId: new PublicKey(ASSOCIATED_TOKEN_PROGRAM_ID),
    keys: [
      { pubkey: payer, isSigner: true, isWritable: true },
      { pubkey: recipientAta, isSigner: false, isWritable: true },
      { pubkey: recipient, isSigner: false, isWritable: false },
      { pubkey: mint, isSigner: false, isWritable: false },
      { pubkey: SystemProgram.programId, isSigner: false, isWritable: false },
      { pubkey: new PublicKey(TOKEN_PROGRAM_ID), isSigner: false, isWritable: false }
    ],
    data: new Uint8Array([1])
  });
}

function createTransferInstruction(owner, mint, sourceAta, recipientAta) {
  const { PublicKey, TransactionInstruction } = window.solanaWeb3;
  return new TransactionInstruction({
    programId: new PublicKey(TOKEN_PROGRAM_ID),
    keys: [
      { pubkey: sourceAta, isSigner: false, isWritable: true },
      { pubkey: mint, isSigner: false, isWritable: false },
      { pubkey: recipientAta, isSigner: false, isWritable: true },
      { pubkey: owner, isSigner: true, isWritable: false }
    ],
    data: new Uint8Array([12, ...u64Bytes(PREMIUM_PRICE_UNITS), 6])
  });
}

function payerFromParsedTransaction(transaction) {
  return transaction?.transaction?.message?.accountKeys
    ?.find((account) => account.signer)
    ?.pubkey?.toString?.() || "";
}

function hasExpectedUsdcTransfer(transaction) {
  return (transaction?.meta?.postTokenBalances || []).some((post) => {
    const pre = transaction.meta?.preTokenBalances?.find(
      (item) => item.accountIndex === post.accountIndex
    );
    const delta = BigInt(post.uiTokenAmount.amount) - BigInt(pre?.uiTokenAmount.amount || "0");
    return (
      post.mint === SOLANA_USDC_MINT &&
      post.owner === SOLANA_USDC_RECIPIENT &&
      delta >= PREMIUM_PRICE_UNITS
    );
  });
}

async function verifyPaymentOnFrontend(connection, signature, expectedWallet) {
  const transaction = await connection.getParsedTransaction(signature, {
    commitment: "finalized",
    maxSupportedTransactionVersion: 0
  });
  if (!transaction || transaction.meta?.err || !hasExpectedUsdcTransfer(transaction)) {
    return false;
  }
  return payerFromParsedTransaction(transaction) === expectedWallet;
}

async function payWithConnectedWallet() {
  if (!walletState.provider || !walletState.address) {
    setAccessMessage("请先连接钱包。");
    return;
  }

  const { Connection, PublicKey, Transaction } = window.solanaWeb3 || {};
  if (!Connection || !PublicKey || !Transaction) {
    setAccessMessage("Solana 支付组件加载失败，请刷新页面后重试。");
    return;
  }

  els.accessPayButton.disabled = true;
  setAccessMessage("正在唤起钱包，请确认支付 19.9 USDC...");

  try {
    const connection = new Connection(SOLANA_RPC_URL, "confirmed");
    const payer = new PublicKey(walletState.address);
    const recipient = new PublicKey(SOLANA_USDC_RECIPIENT);
    const mint = new PublicKey(SOLANA_USDC_MINT);
    const sourceAta = associatedTokenAddress(payer, mint);
    const recipientAta = associatedTokenAddress(recipient, mint);
    const { blockhash, lastValidBlockHeight } = await connection.getLatestBlockhash("confirmed");
    const transaction = new Transaction({
      feePayer: payer,
      recentBlockhash: blockhash
    });

    transaction.add(createRecipientAtaInstruction(payer, recipient, mint, recipientAta));
    transaction.add(createTransferInstruction(payer, mint, sourceAta, recipientAta));

    let signature;
    if (walletState.provider.signAndSendTransaction) {
      const result = await walletState.provider.signAndSendTransaction(transaction);
      signature = result.signature || result;
    } else if (walletState.provider.signTransaction) {
      const signed = await walletState.provider.signTransaction(transaction);
      signature = await connection.sendRawTransaction(signed.serialize());
    } else {
      throw new Error("当前钱包不支持 Solana 交易签名。");
    }

    setAccessMessage("交易已发送，正在等待链上确认并自动解锁...");
    await connection.confirmTransaction({ signature, blockhash, lastValidBlockHeight }, "confirmed");
    const verified = await verifyPaymentOnFrontend(connection, signature, walletState.address);
    if (!verified) throw new Error("链上未验证到 19.9 USDC 到账，请稍后重试。");
    grantFrontendAccess(walletState.address);
    unlockAccess("支付已通过 Solana RPC 验证，高级权限已解锁。");
  } catch (error) {
    console.warn(error);
    setAccessMessage(error.message || "支付未完成，请检查钱包余额后重试。");
  } finally {
    els.accessPayButton.disabled = false;
  }
}

function solanaAddress(result, provider) {
  return result?.publicKey?.toString?.() || provider?.publicKey?.toString?.() || "";
}

function bindWalletAccountEvents() {
  if (!walletState.provider?.on) return;
  unbindWalletAccountEvents();
  walletState.accountChangedHandler = async (publicKey) => {
    const address = publicKey?.toString?.() || "";
    if (address === walletState.address) return;
    walletState.address = address;
    renderWalletState();
    lockAccessGate("钱包账户已切换，请重新支付或等待自动查账。");
    clearFrontendAccess();
    if (!address) return;
    renderAccessPayment();
  };
  walletState.accountsChangedHandler = (accounts) => {
    const address = Array.isArray(accounts) ? accounts[0] || "" : "";
    walletState.accountChangedHandler(address);
  };
  walletState.provider.on("accountChanged", walletState.accountChangedHandler);
  walletState.provider.on("accountsChanged", walletState.accountsChangedHandler);
}

function unbindWalletAccountEvents() {
  if (walletState.provider?.removeListener && walletState.accountChangedHandler) {
    walletState.provider.removeListener("accountChanged", walletState.accountChangedHandler);
  }
  if (walletState.provider?.removeListener && walletState.accountsChangedHandler) {
    walletState.provider.removeListener("accountsChanged", walletState.accountsChangedHandler);
  }
  walletState.accountChangedHandler = null;
  walletState.accountsChangedHandler = null;
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
      bindWalletAccountEvents();
      renderWalletState();
      setWalletMessage("钱包已连接，请直接发起支付交易。");
      renderAccessPayment();
    }
  } catch (error) {
    console.warn(error);
    if (walletState.address) {
      renderAccessPayment();
      setAccessMessage(error.message || "钱包已连接，请直接发起支付交易。");
      setWalletMessage("钱包已连接，请直接发起支付交易。");
    } else {
      setWalletMessage("连接已取消或失败，请重试。");
    }
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
  if (walletState.paymentCheckInFlight) return;
  const checkedWallet = walletState.address;
  walletState.paymentCheckInFlight = true;
  setAccessStep("verify");
  setAccessMessage("正在检查链上到账...");
  els.accessCheckButton.disabled = true;

  try {
    const { Connection, PublicKey } = window.solanaWeb3 || {};
    if (!Connection || !PublicKey) {
      throw new Error("Solana 支付组件加载失败，请刷新页面后重试。");
    }
    const connection = new Connection(SOLANA_RPC_URL, "confirmed");
    const signatures = await connection.getSignaturesForAddress(
      new PublicKey(walletState.address),
      { limit: 20 },
      "finalized"
    );
    let verified = false;
    for (const item of signatures) {
      if (item.err) continue;
      verified = await verifyPaymentOnFrontend(connection, item.signature, walletState.address);
      if (verified) break;
    }
    if (!verified) {
      setAccessMessage("暂未检测到到账。付款完成后系统会继续自动检查。");
      setAccessStep("payment");
      return;
    }
    if (checkedWallet !== walletState.address) return;

    grantFrontendAccess(walletState.address);
    unlockAccess("支付已通过 Solana RPC 验证，高级权限已解锁。");
  } catch (error) {
    console.warn(error);
    setAccessMessage(error.message || "支付状态检查失败，请稍后重试。");
    setAccessStep("payment");
  } finally {
    walletState.paymentCheckInFlight = false;
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
    unbindWalletAccountEvents();
    if (walletState.provider?.disconnect) await walletState.provider.disconnect();
  } catch (error) {
    console.warn(error);
  }
  walletState.provider = null;
  walletState.address = "";
  walletState.name = "";
  clearFrontendAccess();
  renderWalletState();
  setWalletMessage("钱包已断开。");
  unlockAccess();
}

async function restoreAuthorizedSession() {
  const access = storedFrontendAccess();
  if (access) {
    grantFrontendAccess(access.walletAddress);
    unlockAccess("高级权限已恢复。");
  }
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
  els.accessPayButton.addEventListener("click", payWithConnectedWallet);
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".wallet-control")) setWalletMenu(false);
  });
  renderWalletState();
  unlockAccess();
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
            <strong>${teamLabel(team)}</strong>
            <span>${team.code} - ${team.confederation} - ${team.form}</span>
          </div>
          <div class="bar" aria-label="${team.name} win probability ${team.probability}%"><span style="width:${width}%"></span></div>
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
            <strong class="team-title">
              <span class="flag-emoji" aria-hidden="true">${team.flagEmoji || ""}</span>
              <span>${team.name}</span>
            </strong>
          </a>
          <span>${team.code} - Group ${team.group}</span>
        </div>
        <div class="team-meta">
          <span>${team.confederation}</span>
          <span>${team.probability.toFixed(1)}%</span>
          <span>${team.form}</span>
        </div>
        <a class="squad-link" href="./team.html?team=${encodeURIComponent(team.code)}">
          View full ${window.WORLD_CUP_SQUADS?.[team.code]?.length || team.players.length} player squad
        </a>
      </article>
    `)
    .join("");
}

function renderWatchGuide() {
  if (!els.watchGuideCalendar) return;
  const highlights = [
    {
      date: "2026-06-12 03:00 BJT",
      stage: "Opening match",
      title: `${teamLabel(teamByCode("MEX"))} vs ${teamLabel(teamByCode("RSA"))}`,
      detail: "Estadio Azteca, Mexico City"
    },
    {
      date: "2026-06-13 06:00 BJT",
      stage: "Host debut",
      title: `${teamLabel(teamByCode("CAN"))} vs ${teamLabel(teamByCode("BIH"))}`,
      detail: "BMO Field, Toronto"
    },
    {
      date: "2026-06-13 10:00 BJT",
      stage: "Host debut",
      title: `${teamLabel(teamByCode("USA"))} vs ${teamLabel(teamByCode("PAR"))}`,
      detail: "SoFi Stadium, Los Angeles"
    },
    {
      date: "2026-07-20 03:00 BJT",
      stage: "Final",
      title: "World Cup Final",
      detail: "MetLife Stadium, New York New Jersey"
    }
  ];
  const calendar = buildGroupSchedule();
  els.watchGuideCalendar.innerHTML = `
    <div class="watch-highlights">
      ${highlights.map((item) => `
        <article class="watch-highlight">
          <span>${item.date}</span>
          <strong>${item.title}</strong>
          <small>${item.stage}</small>
          <p>${item.detail}</p>
        </article>
      `).join("")}
    </div>
    <div class="schedule-calendar">
      ${calendar.map((item) => `
        <article class="schedule-day">
          <div class="schedule-cell matchup">
            <span>Matchup</span>
            <strong>${teamLabel(item.home)} <b>vs</b> ${teamLabel(item.away)}</strong>
          </div>
          <div class="schedule-cell">
            <span>Beijing time</span>
            <time>${item.bjt}</time>
          </div>
          <div class="schedule-cell">
            <span>Group</span>
            <strong>${item.group} · ${item.label}</strong>
          </div>
          <div class="schedule-cell venue">
            <span>Venue</span>
            <strong>${item.venue}</strong>
          </div>
          <div class="schedule-score">
            <span>Score</span>
            <strong>${item.score}</strong>
          </div>
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
            <strong>${player.name}</strong>
            <span>${player.team} - ${player.position}</span>
          </div>
          <span class="tag">${player.rating.toFixed(1)}</span>
        </div>
        <p class="hint">${player.reason}</p>
      </article>
    `)
    .join("");
}

function renderMatchEvents(events) {
  if (!events.length) return '<p class="live-empty-detail">No key events yet</p>';
  return `
    <div class="live-events">
      ${events.slice(-5).reverse().map((event) => `
        <div>
          <strong>${event.time ?? "-"}'</strong>
          <span>${event.team} - ${event.type}${event.detail ? ` - ${event.detail}` : ""}</span>
          <small>${event.player || ""}</small>
        </div>
      `).join("")}
    </div>
  `;
}

function renderLiveMatches(payload) {
  if (!els.liveMatchList) return;
  els.footballUpdatedAt.textContent = payload.configured
    ? `Updated: ${formatDate(payload.updatedAt)}`
    : "Waiting for kickoff";

  if (!payload.liveMatches.length) {
    els.liveMatchList.innerHTML = `
      <div class="live-empty">
        <strong>Waiting for kickoff</strong>
        <span>Scores and events will refresh every 15 seconds after matches begin.</span>
      </div>
    `;
    return;
  }

  els.liveMatchList.innerHTML = payload.liveMatches.map((match) => `
    <article class="live-match-card">
      <div class="live-match-meta">
        <span class="live-badge">${match.status} - ${match.elapsed ?? "-"}'</span>
        <span>${match.round}${match.venue ? ` - ${match.venue}` : ""}</span>
      </div>
      <div class="live-score">
        <div><strong>${matchTeamLabel(match.home.name)}</strong><span>Home</span></div>
        <b>${match.home.score ?? 0} - ${match.away.score ?? 0}</b>
        <div><strong>${matchTeamLabel(match.away.name)}</strong><span>Away</span></div>
      </div>
      ${renderMatchEvents(match.events)}
    </article>
  `).join("");
}

function renderStandings(payload) {
  if (!els.standingsList) return;
  if (!payload.standings.length) {
    els.standingsList.innerHTML = '<p class="live-empty-detail">Waiting for kickoff</p>';
    return;
  }

  els.standingsList.innerHTML = payload.standings.map((group) => `
    <section class="standing-group">
      <h4>${group[0]?.group || "Group"}</h4>
      ${group.map((row) => `
        <div class="standing-row">
          <span>${row.rank}</span>
          <strong>${matchTeamLabel(row.team.name)}</strong>
          <b>${row.points}</b>
        </div>
      `).join("")}
    </section>
  `).join("");
}

async function refreshLiveFootball() {
  if (!accessState.unlocked) return;
  try {
    const response = await fetch("/api/football/live-matches", {
      headers: { Accept: "application/json" }
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "赛事 API 请求失败");
    renderLiveMatches(payload);
    renderStandings(payload);
  } catch (error) {
    console.warn(error);
    renderLiveMatches({
      configured: false,
      liveMatches: [],
      updatedAt: new Date().toISOString()
    });
    renderStandings({ standings: [] });
  }
}

function renderSportsNews(payload) {
  if (!els.sportsNewsList || !els.sportsNewsUpdatedAt) return;
  els.sportsNewsUpdatedAt.textContent = payload.stale
    ? "Recent snapshot"
    : `Updated: ${new Intl.DateTimeFormat("zh-CN", { timeStyle: "short" }).format(new Date(payload.updatedAt))}`;
  els.sportsNewsList.innerHTML = payload.articles.length
    ? payload.articles.slice(0, 6).map((article) => `
      <article class="sports-news-card">
        ${article.imageUrl ? `<img src="${escapeHtml(article.imageUrl)}" alt="" loading="lazy" />` : ""}
        <div>
          <span>${escapeHtml(article.source)}</span>
          <h4><a href="${escapeHtml(article.link)}" target="_blank" rel="noreferrer">${escapeHtml(article.title)}</a></h4>
        </div>
      </article>
    `).join("")
    : '<p class="live-empty-detail">Sports news is temporarily unavailable. Please try again later.</p>';
}

async function refreshSportsNews() {
  if (!accessState.unlocked) return;
  try {
    const response = await fetch("/api/news/sports", { headers: { Accept: "application/json" } });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "体育新闻请求失败");
    renderSportsNews(payload);
  } catch (error) {
    console.warn(error);
    renderSportsNews({ articles: [], stale: true, updatedAt: new Date().toISOString() });
  }
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
              <span>${player.years} ? ${player.note}</span>
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
            <h4>${edition.year} ? ${edition.host}</h4>
            <p><strong>Champion: </strong>${edition.champion}</p>
            <p><strong>Runner-up: </strong>${edition.runnerUp}</p>
            <p><strong>Teams: </strong>${edition.teams}</p>
            <p>${edition.notableSquads}</p>
          </article>
        `).join("")}
    </div>
  `;
}

function renderMeta() {
  els.updatedAt.textContent = `Updated: ${formatDate(state.data.meta.updatedAt)}`;
  els.editionCount.textContent = state.data.historicalEditions.length;
}

function render() {
  renderMeta();
  renderContenders();
  renderWatchGuide();
  renderMvp();
  renderTeams();
  renderHistory();
}

function setRefreshLabel(text) {
  els.refreshState.textContent = text;
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

setupFilters();
setupWallet();
render();
