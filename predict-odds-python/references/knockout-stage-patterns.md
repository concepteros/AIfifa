# 淘汰赛/16强投注模式（2026-06-30 提炼）

## 核心发现

### 平局概率飙升
- 6/29 三场淘汰赛：2场90分钟平局（Germany 1-1 Paraguay, Netherlands 1-1 Morocco）
- 淘汰赛开局保守 — 宁愿拖入加时也不冒险进攻
- Draw 赔率在淘汰赛阶段被系统性低估 — 市场未完全定价淘汰赛平局溢价

### 数据稀疏性
- 淘汰赛球队在 fbref.csv 中仅 1-2 场真实赛果
- Poisson 模型在 `matches_used ≤ 2` 时不可信
- 预测必须以 Bet365/Pinnacle 赔率为准，模型仅作参考

### 大小球线下移
- 淘汰赛大小球线明显低于小组赛同等实力对决
- Mexico vs Ecuador: Pinnacle O1.75（小组赛同等实力通常 O2.25+）
- 淘汰赛 Under 方向有系统性 value

### 碾压级框架仍部分有效
- France vs Sweden: 1.30 赔率，接近碾压级
- 对手（Sweden）无五大联赛中场核心+速度型边锋 → 无结构化防反
- → France 可走波胆+Over 路线

### 名气溢价框架验证
- Norway (FIFA #44) 让 Ivory Coast (非洲冠军) 球 — Haaland 溢价仍在
- Norway vs Ivory Coast: Norway @ 2.19 隐含 46%
- Haaland 小组赛有进球（vs France）→ 溢价可信度中等
- 但 Norway 1-4 被法国屠杀 — 防守端有漏洞

## 分析管线调整

淘汰赛阶段分析管线（替代小组赛管线）：
1. ESPN 赛果回顾（两队小组赛表现）
2. Poisson 模型预测（data仅参考，以赔率为准）
3. The Odds API 三线赔率（h2h + totals + spreads）
4. 战术对位（analyze_tactical_matchup）
5. 淘汰赛特殊因子：①平局溢价 ②数据稀疏 ③Under偏向 ④名气溢价延续
6. 投注建议

## 6/30 实测案例

| 场次 | 赔率区间 | 方向 | 原因 |
|------|---------|------|------|
| France vs Sweden | 1.30 近碾压 | Over 2.5 @ 1.44 | 对手无防反结构，法国小组赛3场均3+球 |
| Mexico vs Ecuador | 灰色区偏墨 | Under 2.5 @ 1.40 | 两队近6场仅7球，淘汰赛保守+防守硬 |
| IC vs Norway | Haaland溢价 | 观望/小注平局 | 数据最稀疏，16强开场高不确定性 |
