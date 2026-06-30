# api-football 数据富化管线

## 概述

`scripts/enrich_wc_data.py` — 用 api-football 真实赛果覆盖模拟数据，并用 FIFA 排名点估计 xG。

## 工作流

```
api-football fixtures (Jun 20-22)     Wikipedia FIFA Rankings
         │                                      │
         ▼                                      ▼
   真实比分 (6场已完赛)                  FIFA_POINTS dict (48队)
         │                                      │
         └────────────┬─────────────────────────┘
                      ▼
              fbref_merged.csv
              (真实覆盖 + 模拟留存 + 合成兜底)
```

## xG 估算公式

当 api-football 不返回 xG（免费计划限制）时，从比分反推：

```python
base = {0: 0.4, 1: 1.0, 2: 1.7, 3: 2.4, 4: 3.0, 5: 3.5}
elo_diff = (fifa_self - fifa_opp) / 100
xG = base[goals] * (1.0 + clamp(elo_diff * 0.05, -0.2, 0.3))
```

## 免费计划限制

- **日期范围**：仅 2026-06-20 至 2026-06-22
- **xG 数据**：不返回 Expected Goals（需付费）
- **赛季过滤**：`league=1&season=2026` 返回空（需 season=2022-2024）
- **统计端点**：`/fixtures/statistics` 多数场次返回空
- **调用上限**：100次/天

## FIFA 排名数据源

从 Wikipedia `FIFA Men's World Ranking` 页面抓取 top 20（截至 2026-06-11）：

```
browser_navigate → wikipedia.org/wiki/FIFA_Men's_World_Ranking
browser_console → document.querySelectorAll('table.wikitable tbody tr')
```

剩余 28 队按已知排名区间估算（±50 点精度）。

## 输出格式

CSV 兼容 `data_sources.load_matches()`：
```
date,league,team,opponent,venue,goals_for,goals_against,xg,xga,result
2026-06-20,FIFA World Cup,Brazil,Haiti,home,3,0,2.96,0.32,W
2026-06-10,Friendly,Spain,Local XI,neutral,1,1,2.38,1.2,D  ← 合成占位
```

## 待改进

- 真实比赛踢完后，用 `enrich_matchday()` 增量更新
- 付费 api-football 计划可获取 xG、球员统计
- 集成更多数据源（FotMob、Opta）交叉验证
