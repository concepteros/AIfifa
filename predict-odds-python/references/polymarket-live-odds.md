# Polymarket 实时盘口抓取

用于 football-bot 深度分析 — 抓取单场比赛的 Moneyline/Spread/Total 实时赔率。

## 浏览器工作流

1. 导航到搜索页
```
browser_navigate → https://polymarket.com/sports/fifa/soccer
```

2. 搜索比赛
```
browser_type → ref=e52 (search box) → "Tunisia Japan"
browser_press → Enter
browser_snapshot → 查找 match link (如 ref=e81 "Tunisia vs. Japan")
```

3. 进入比赛页
```
browser_click → ref=e81
browser_snapshot → 提取盘口数据
```

## 数据提取

从 snapshot 文本中提取：

- **比赛状态**: "完赛" + 比分 → 已结束；"1时 52分 33秒" → 倒计时
- **Moneyline**: `TUN12¢` / `DRAW21¢` / `JPN69¢` → 概率 12%/21%/69%
- **Spread**: `TUN +1.5 60¢` / `JPN -1.5 41¢`
- **Total**: `O 2.5 47¢` / `U 2.5 54¢` → 大/小球
- **交易量**: `$7.35M Vol.` → 总交易量

## 示例输出（Tunisia vs Japan, 2026-06-21）

```
Polymarket 实时盘口 — Tunisia vs Japan（12:00 BJT）
$7.35M 交易量

Moneyline: TUN 12% / DRAW 21% / JPN 69%
Spread: TUN +1.5 60% / JPN -1.5 41%
Total: O 2.5 47% / U 2.5 54%

市场共识：日本胜（69%）、≤1球差（+1.5 突尼斯 60%）、小球（54%）
```

## 注意事项

- Polymarket 自动重定向到 `/zh/` 中文界面
- 价格单位为 USDC 美分（12¢ = $0.12 = 12% 概率）
- 已完成比赛不要推荐下注
- 浏览器数据是实时的，Gamma API 不可靠不要用
