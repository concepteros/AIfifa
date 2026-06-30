# 预测输出标准 (v1.7 — 2026-06-22 用户确认)

用户规定：「以后核心预测数据按这个来」。本标准为强制规范。

## 触发条件

用户说「预测」「分析」「明天比赛」「今日赛程」时，必须按本标准输出。

## 数据采集流程 (强制顺序)

1. **api-football** — 拉取赛程（`/fixtures?date=`）+ 过滤 World Cup (league=1) + BJT 00:00-23:59 过滤
2. **api-football** — 拉取 Bet365 赔率（`/odds?fixture=&bookmaker=8`）
3. **Poisson 模型** — `predict_match(features['features'], odds=None)` 纯数据预测
4. **tactics.py** — `generate_tactical_analysis(home, away)` 战术对位
5. **supplementary.py** — `referee_impact_summary()` 裁判评估
6. **sentiment.py** — 可选（耗时 20s+，网络慢时跳过）
7. **投注建议** — 对比模型概率 vs Bet365 隐含概率

## 每场比赛输出格式

```
⚽ HH:MM BJT | Home vs Away  [方向胜X%]

模型:
  xG H.AA - A.AA | 胜平负: 主X%/平X%/客X%
  大小球: 大2.5 X% / 小2.5 X%
  波胆: X-X (X%) / X-X (X%) / X-X (X%)
  角球: ~X个

盘口 (Bet365):
  主X / 平X / 客X → 隐含 X%/X%/X%
  大2.5 @X / 小2.5 @X

战术:
  [tactics.py 输出摘要，200字内]

裁判:
  [referee_impact_summary 输出]

投注建议:
  [推荐] @X (信心 ⭐)
  [备选] @X
```

## 波胆选取规则

**禁止直接使用模型 `most_likely_scores[0]`** 当比分与实力差距明显矛盾时。

检查规则：
- 如果模型输出「1-1」但实力差距 > 1.5 tier 且盘口主胜 < 1.20，模型波胆不可信
- 这种情况下结合盘口 `Exact Score` 最低赔率 + 战术分析人工调整
- 例如：Spain vs Saudi（模型 1-1 10%，盘口 Spain 1.11）→ 人工调整为 2-0 或 3-0

## Edge 可信度规则

**模型偏离盘口有两种情况，需区分：**

### 情况 A：合成数据高估弱队（v1.7，已基本解决）
- 特征：模型给弱队太高概率，盘口显示强队碾压
- 示例：Spain 58% vs 盘口 86%（合成数据时期）

### 情况 B：单场数据低估强队（v2.0，当前主要问题）
- 特征：仅 1 场真实赛果，失常表现主导模型
- 示例：Spain 0-0 Cape Verde（失常）→ 预测 Spain vs Saudi 仅 35%（盘口 86%）
- 判断：`matches_used ≤ 2` → **禁止用模型 Edge 做决策**

### 通用规则
- 模型概率与 Bet365 隐含概率差距 ≤ 10pp → Edge 可信，纳入投注决策
- 差距 10-20pp → 谨慎，结合战术/裁判综合判断
- 差距 > 20pp → **Edge 不可信，是模型系统性偏差**。以市场赔率为准，勿用模型 Edge 做决策
- 当 `matches_used ≤ 2` 时，无论差距多少，**必须标注「数据不足，以盘口为准」**

详见 `references/single-match-overfit.md`。

## 投注建议规则

- 赔率 < 1.20 → 标注「无投注价值」，不推荐
- 赔率 1.20-1.50 → 推荐但降信心
- 赔率 1.50-2.50 → 正推荐
- 赔率 > 2.50 → 高赔投机，标注风险

## 数据真实性标准

- ✅ api-football 数据 → 可直接引用，不需要标注
- ✅ Bet365 盘口 → 可直接引用
- ❌ supplementary.py 伤病 → 合成数据，**禁止当真实情报引用**
- ❌ data_enrichment.py 统计 → 合成数据，需标注「模拟」
- ✅ 裁判分配 → 合成但合理（无真实裁判任命），可引用但说明来源

## 复盘对比格式

当比赛完赛后，输出：
```
实际: X-X (半场 X-X)
  射门: H-A | 射正: H-A | 控球: H%-A% | 角球: H-A
  xG: H.AA - A.AA
  进球: [球员] [分钟]
预测 vs 实际: 方向 [✅/❌] | 波胆 [✅/❌] | 大小球 [✅/❌]
```
