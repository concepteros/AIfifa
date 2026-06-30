# 数据真实性：合成 vs 真实

> 🔴 2026-06-22 用户纠正：将合成伤病数据当真实情报引用导致信任危机。

## 合成数据（不可当真）

| 文件 | 内容 | 说明 |
|------|------|------|
| `supplementary.py` `_INJURY_REPORTS` | Courtois/Rodri/Neymar/Odegaard 等伤病 | 全部预编，非真实新闻 |
| `data_enrichment.py` `TEAM_TIERS` | 48 队 xG/射门/控球范围 | 按 FIFA 档位估算，非真实采集 |
| `data_enrichment.py` `WC2026_GROUPS` | 小组赛分组 | 基于实力平衡模拟，非官方抽签 |
| `data_enrichment.py` `_build_match_rows()` | 模拟赛果 | 按档位差随机生成 |
| `data/fbref.csv` | 历史比赛数据 | 合成/估算，非 FBref 真实下载 |

## 可用真实数据源

| 来源 | 覆盖面 | 获取方式 |
|------|--------|----------|
| **api-football** (v3.football.api-sports.io) | ✅ 世界杯 fixtures + 庄家赔率 + 球员名单 | `API_FOOTBALL_KEY` in `.env`，免费 100次/天 |
| **The Odds API** | ⚠️ 赛程有，赔率需付费 | `THE_ODDS_API_KEY` |
| **Predict.fun** | ✅ 预测市场实时盘口 | `PREDICTFUN_API_KEY` |
| **Sportmonks** | ❌ 2026 世界杯无数据（0 fixtures） | `SPORTMONKS_API_KEY` 已配但无此赛事 |
| **OpenNews MCP** | ❌ 无 2026 世界杯新闻 | 搜索返回空 |

## api-football 验证结果 (2026-06-22)

```
查询: /fixtures?date=2026-06-22 → 返回 0 场
查询: /fixtures?date=2026-06-21 → 返回 336 场（含 WC matches）
  ✅ Ecuador 0-0 Curaçao [FT]
  ✅ Tunisia 0-4 Japan [FT]
  ✅ Spain vs Saudi Arabia [NS]
  ✅ Belgium vs Iran [NS]
  ✅ Uruguay vs Cape Verde [NS]

查询: /fixtures?date=2026-06-22 WC 场次
  ✅ New Zealand vs Egypt [NS] ID=1489396
  ✅ Argentina vs Austria [NS] ID=1489399
  ✅ France vs Iraq [NS] ID=1539017

赔率 (/odds?fixture=1489396):
  ✅ Bet365: 主5.50/平4.20/客1.57, 大2.5@2.10/小2.5@1.73
  ✅ 角球 Over 8.5@1.73, BTTS Yes 2.20/No 1.62
  ✅ 球员道具: Salah, Wood, Marmoush 等

阵容 (/fixtures/lineups?fixture=1489394):
  ✅ Tunisia 3-4-2-1, Japan 3-4-2-1
  ✅ 真实球员名: Tomiyasu, Doan, Itakura 等
```

## 规则

1. **禁止**引用 `supplementary.py` 伤病数据做分析。说「Courtois 缺阵」= 撒谎。
2. 预测输出提及伤病/阵容时，必须标注来源：「api-football 数据」或「模拟数据」
3. 庄家操盘分析中只使用真实 API 数据（赔率→api-football/Predict.fun，球员→api-football）
4. 模型预测的底层数据是合成的（tier-based），概率方向可靠但绝对值有偏差。与真实赔率对比时要标注。
