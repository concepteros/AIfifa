# 庄家操盘分析框架

用户可能要求从庄家视角对比赛做全方位分析。以下是必须覆盖的 10 个维度：

## 10 维度清单

| # | 维度 | 数据来源 | 输出要求 |
|---|------|---------|---------|
| 1 | 小组出线形势 | FotMob 历史战绩 + 小组积分榜 | 双方晋级压力，战意 |
| 2 | 实时盘口赔率 | Predict.fun `/v1/search` + Polymarket 浏览器 | 胜平负/让分/大小球，两端对比 |
| 3 | 聪明钱追踪 | OpenNews MCP `CORRELATION_*` / `SMART_MONEY_*` 信号 | 大户方向，对冲意图 |
| 4 | 社会舆论 | OpenNews MCP 新闻搜索 | 媒体叙事，球迷情绪 |
| 5 | 教练情况 | 网络搜索 + tactics.py | 战术倾向，临场调整能力 |
| 6 | 核心球员 | FotMob 数据 + 网络搜索 | 状态，伤病，关键度 |
| 7 | 伤病情况 | supplementary.py | 缺阵影响评估 |
| 8 | 历史交锋 | FotMob CSVs | 近期战绩，心理优势 |
| 9 | 打法风格对比 | tactics.py 战术画像 | 阵型、控球、对位优劣 |
| 10 | 爆冷概率 | 综合评估 | 百分比 + 触发条件 |

## 庄家操盘推演模板

对每场比赛，用以下结构输出庄家视角：

```
### 🧠 庄家操盘

> 一句话定调

1. 盘口信号解读 — 赔率/让分/大小球的异常点
2. 资金流向预判 — 散户会买哪边
3. 庄家收割路径 — 怎样让多数人亏钱
4. 最可能剧本 — 比分 + 过程描述
```

## 输出格式

- 用表格做盘口对比（Predict.fun vs Polymarket）
- 聪明钱信号高亮标注
- 每场给出爆冷概率
- 结尾汇总表：操盘策略 / 收割目标 / 爆冷概率

## 数据采集流程

```bash
# 1. Predict.fun 盘口
cd /path && python -c "from predict_odds.predict_fun_odds import fetch_predict_fun_odds_by_date; ..."

# 2. Polymarket 浏览器
browser_navigate → https://polymarket.com/event/{slug}

# 3. 聪明钱
mcp_opennews_search_news(keyword="{match_name} World Cup")
```
