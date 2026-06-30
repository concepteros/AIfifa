# 2026-06-22 世界杯小组赛复盘

> 4 场全完赛。2 正路 + 2 冷门。核心教训：1.35-1.45 区间全翻，比利时黄金一代已死，xG 转化方向性不对称。

## 比赛结果总览

| # | 比赛 | BJT | 比分 | 赛前 ML | 隐含概率 | 结果 | 爆冷 |
|---|------|-----|------|---------|---------|------|------|
| 1 | Spain vs Saudi Arabia | 00:00 | 4-0 | 1.10/10.00/21.00 | Spain 90.9% | 正路 ✅ | — |
| 2 | Belgium vs Iran | 03:00 | 0-0 | 1.38/4.90/8.00 | Belgium 72.5% | 平局 | 🔴 大冷 |
| 3 | Uruguay vs Cape Verde | 06:00 | 2-2 | 1.40/4.33/9.00 | Uruguay 71.4% | 平局 | 🟡 小冷 |
| 4 | New Zealand vs Egypt | 09:00 | 1-3 | 6.00/4.20/1.55 | Egypt 64.5% | 正路 ✅ | — |

---

## 逐场深度复盘

### ① Spain 4-0 Saudi Arabia — 碾压正路

**Pre-match:**
- Bet365: Spain 1.10, Draw 10.00, Saudi 21.00
- Over 3.5 @ 1.91, BTTS No @ 1.40
- Spain (4-3-3, de la Fuente) — Yamal/Olmo/Pedri/Rodri 全主力
- Saudi (5-4-1, Mancini) — 5 后卫大巴

**Stats:**
| | Spain | Saudi Arabia |
|---|-------|-------------|
| Shots (on target) | 22 (8) | 3 (1) |
| Shots inside box | 13 | **0** |
| xG | 2.85 | 0.14 |
| Possession | 67% | 33% |

**Key takeaway:** Spain xG 2.85 → 4 goals (+1.15 overperformance). Saudi had ZERO shots inside box — Mancini's 5-defender block completely neutralized. Over 3.5 @1.91 was the best value bet.

---

### ② 🔴 Belgium 0-0 Iran — 黄金一代确诊死亡

**Pre-match:**
- Bet365: Belgium 1.38, Draw 4.90, Iran 8.00
- Over 2.5 @ 1.80, BTTS No @ 1.70
- Belgium (4-2-3-1, Garcia) — Courtois, KDB, Lukaku, Trossard **ALL started**
- Iran (5-4-1, Ghalenoei) — 低位防守，Taremi 单箭头

**Stats:**
| | Belgium | Iran |
|---|---------|------|
| Shots (on target) | 23 (7) | 7 (3) |
| Shots inside box | 20 | 6 |
| xG | 1.80 | 0.63 |
| Possession | 70% | 30% |
| Red cards | 🔴 1 | 0 |
| GK Saves | 3 | **7** |

**Why 0-0:**
1. **Red card** — Belgium went down to 10 men (exact player TBD)
2. **Beiranvand heroics** — 7 saves, goals_prevented 1.70
3. **Lukaku finishing failure** — 20 box shots, only 7 on target, 0 goals
4. **Low block broke KDB** — Iran's 5-4-1 denied central passing lanes, Belgium resorted to wide crosses

**Betting lesson:**
- Draw @4.90 was the highest-value outcome
- Under 2.5 @2.00 paid despite Belgium's 1.80 xG — **xG is not goals vs low blocks**
- Belgium's `ageing golden generation` weakness (flagged in tactics.py) was decisive

**Future bet against Belgium:** Until they prove otherwise, fade Belgium ML. Under 2.5 + opponent +AH are the defaults.

---

### ③ 🟡 Uruguay 2-2 Cape Verde — Bielsa 体系的血腥代价

**Pre-match:**
- Bet365: Uruguay 1.40, Draw 4.33, Cape Verde 9.00
- Over 2.5 @ 2.30, BTTS Yes @ 2.62
- Uruguay (4-1-4-1, Bielsa) — Valverde, Bentancur, Ugarte 中场铁三角
- Cape Verde (4-1-4-1) — **NOT in tactics.py database** (弱队盲区)

**Stats:**
| | Uruguay | Cape Verde |
|---|---------|-------------|
| Shots (on target) | 16 (2) | 7 (2) |
| Shots inside box | 8 | **1** |
| xG | 2.28 | **0.77** |
| Possession | 66% | 34% |
| Yellow cards | 2 | 1 |

**Why 2-2:**
1. Uruguay xG 2.28 → 2 goals (in line). Bielsa system generates offense.
2. Cape Verde xG 0.77 → 2 goals (**+1.23 overperformance**). Only 1 box shot, but 100% shot conversion (2/2 on target).
3. Uruguay's `over-aggression (cards)` weakness showed — 2 yellows disrupted pressing rhythm
4. Bielsa's high-risk defense was caught twice on the counter

**Betting lesson:**
- BTTS Yes @2.62 was the best value — Bielsa's system = both teams score
- Bielsa teams are **Over 2.5 ATMs** regardless of opponent
- Cape Verde was unprofiled by tactics.py — **weak teams missing from tactics DB are a recurring gap**

---

### ④ New Zealand 1-3 Egypt — Salah+Marmoush 双核奏效

**Pre-match:**
- Bet365: NZ 6.00, Draw 4.20, Egypt 1.55
- Over 2.5 @ 2.00, BTTS Yes @ 2.05
- Egypt (4-2-3-1, Hassan) — Salah + Marmoush starting
- NZ (4-2-3-1, Bazeley) — Wood target man

**Stats:**
| | New Zealand | Egypt |
|---|-------------|-------|
| Shots (on target) | 11 (5) | 19 (7) |
| Shots inside box | 6 | 12 |
| xG | 1.12 | 1.96 |
| Possession | 44% | 56% |

**Key takeaway:** Egypt xG 1.96 → 3 goals (+1.04, moderate overperformance). Salah-dependency didn't materialize — Marmoush shared the creative burden. Egypt ML + Over 2.5 + BTTS Yes all hit. Textbook chalk that delivered.

---

## 三条持久教训

### 1. 1.35-1.45 = 世界杯小组赛 R2 死亡区间（2/2 全翻）

小组赛第二轮强队先胜后松懈 + 弱队拼死抢分 → 平局率远超市场定价。此区间不碰 ML。默认走 Under 2.5 或对手 +AH。

### 2. xG 转化方向性不对称

| 场景 | xG→进球 | 机制 |
|------|---------|------|
| 强队 vs 低 block | 高估 | 大巴压缩空间，射门质量差 |
| 弱队 vs 强队 | 低估 | 士气加成，射门少但每次都是反击好机会 |

**Rule:** 强队低赔 + 对手大巴 → 不要走 Over（即使 xG 2.0+）；弱队 BTTS Yes 比模型概率更有价值。

### 3. 弱队不在 tactics.py 数据库中

Cape Verde 无法进行战术分析。对于未收录的弱队，只能依赖 ESPN/api-football 的赛果和赔率数据。未来遇到类似情况应明确告知用户「此队无战术数据，以赔率+赛果为准」。

---

## 投注成绩单

| 策略 | 赔率 | 结果 |
|------|------|------|
| Spain Over 3.5 | 1.91 | ✅ |
| Belgium Under 2.5 | 2.00 | ✅ |
| Belgium Draw | 4.90 | ✅ |
| Uruguay BTTS Yes | 2.62 | ✅ |
| Uruguay Over 2.5 | 2.30 | ✅ |
| Egypt ML | 1.55 | ✅ |
| Egypt Over 2.5 | 2.00 | ✅ |
| **假想组合回报** | **~120x** | — |
