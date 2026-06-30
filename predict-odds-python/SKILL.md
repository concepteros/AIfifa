---
name: football-bot
description: "AI 足球博彩机器人 — 扫描世界杯/联赛赛事、Poisson 预测、Kelly 下注、Predict.fun 钱包。"
version: 2.2.0
trigger:
  - 用户说"足球"/"fb"/"⚽"/"扫描足球"/"足球赛程"/"足球分析"/"比分预测"
  - 用户说"下注"/"买"/"bet" + 盘口名
  - 用户问"今天有什么比赛"
---

# 足球博彩机器人 (Football Prediction Bot)

AI 驱动的足球预测 + 自动交易系统。Poisson 模型 + 战术分析 + 裁判评估 + 市场赔率交叉验证，Predict.fun 链上下单。

## 快速开始

```bash
cd /Users/macbook/AIfifa/predict-odds-python
source .env  # 或 export $(grep -v '^#' .env | xargs)

# 扫描今日赛事
.venv/bin/python -m predict_odds scan --config data/bot-scan.json --summary

# 深度分析
.venv/bin/python -m predict_odds analyze --match out/2026-06-30-team1-vs-team2.json --no-prompt
```

## 核心管线（6步）

1. **ESPN API** — 赛程/赛果/积分榜（免密钥）
2. **Poisson 模型** — xG 预期进球 + 波胆概率分布
3. **tactics.py** — 59队战术画像 + 风格对位分析
4. **supplementary.py** — 裁判风格评估（严格度/出牌/VAR/偏袒）
5. **The Odds API** — Bet365/Pinnacle 实时赔率（h2h + totals + spreads）
6. **Kelly Criterion** — 1/4 Kelly 仓位计算，单注上限5%

## 数据源

| 数据源 | 用途 | 密钥 |
|--------|------|------|
| ESPN API | 赛程/赛果（免密钥） | 无 |
| The Odds API | 实时赔率 h2h/totals/spreads | THE_ODDS_API_KEY |
| Predict.fun | 链上预测市场盘口+交易 | PREDICTFUN_API_KEY |
| api-football | Bet365赔率/阵容/角球 | API_FOOTBALL_KEY |

## 已验证预测记录

| 比赛 | 预测 | 实际 | 状态 |
|------|------|------|------|
| Ecuador vs Curaçao | 0-0 (平70%) | 0-0 | ✅ 波胆命中 |
| Tunisia vs Japan | 客81% 0-2 | 0-4 | ✅ 方向命中 |
| France vs Iraq | Over 2.5 + 波胆3-0 | 3-0 | ✅ 波胆精准命中 |
| Argentina vs Austria | Under 2.5 + 1-0波胆 | 2-0 (U✅) | ⚠️ |
| Portugal vs Uzbekistan | 碾压穿盘 | 5-0 | ✅ 穿盘 |
| England vs Ghana | 碾压穿盘 | 0-0 | ❌ 框架修正 |
| Panama vs Croatia | 灰色Croatia穿 | 0-1 | ✅ 穿盘 |
| Colombia vs Congo DR | 灰色Colombia穿 | 1-0 | ✅ 穿盘 |

## 已知陷阱

- **模型系统性高估弱队**：合成 fbref.csv 数据抹平实力差距。模型 vs 市场差距 >20pp 时以市场赔率为准
- **单场数据过拟合**：matches_used ≤2 时禁止以模型概率为准
- **合成数据 ≠ 真实情报**：supplementary.py 伤病数据全是模拟，不可当真
- **三级赔率框架**：1.06-1.18 碾压级 / 1.35-1.45 危险区 / 1.48-1.60 灰色区
- **结构化防反检查**：碾压级前检查对手是否有五大联赛中场核心+速度边锋
- **名气溢价**：Haaland 类超级球星让弱队开让球，首轮爆发=可信，首轮沉寂=虚假
- **淘汰赛平局率高**：16强开始平局概率显著上升，ML下注需保守

## Predict.fun 交易

```bash
# 下注（默认 dry-run）
.venv/bin/python -m predict_odds bet --match-slug fifwc-tun-jpn-2026-06-21 \
  --bet-type away --amount 10 --dry-run -y

# 实盘
.venv/bin/python -m predict_odds bet ... --live -y

# bet-type: home / draw / away / over_2_5 / under_2_5 / exact_score_1-0
# 安全闸: 单注≤$50，日限额$200
# 链: BNB Chain (ChainId 56)，需 USDC + BNB gas
```

## Kelly 参数

- 资金池: 100 USDC
- 1/4 Kelly (fractional_kelly=0.25)
- 单注上限 5% (max_stake_fraction=0.05)
- 最小 Edge: 3pp (min_edge=0.03)

## Cron

| Job | ID | Schedule | Status |
|-----|-----|----------|--------|
| 足球每日赛程 | a7571a5f41e0 | 每日 08:00 BJT | Active |

## 项目结构

```
predict-odds-python/
├── src/predict_odds/     # 核心模块
│   ├── prediction.py     # Poisson v2 模型
│   ├── feature_pipeline.py # 特征工程+裁判集成
│   ├── tactics.py        # 59队战术画像
│   ├── supplementary.py  # 裁判/天气/伤病
│   ├── ml_model.py       # XGBoost 混合预测
│   ├── the_odds_api.py   # The Odds API client
│   ├── bot_scanner.py    # 扫描+Kelly管线
│   ├── predict_fun_betting.py  # 链上下单
│   └── predict_fun_sell.py     # 止盈模块
├── data/                 # 数据文件
├── scripts/              # 数据管线脚本
├── references/           # 分析框架文档
└── tests/                # 测试套件
```

## 环境依赖

- Python 3.9+（macOS 默认 3.9.6）
- `.env` 位于项目根目录
- 虚拟环境: `.venv/bin/python`
- BNB Chain USDC + BNB gas（Predict.fun 交易）
