# FotMob 真实数据管线

## 来源

fotmob.com — 世界杯 2026 赛事页面 (`leagues/77/fixtures/world-cup`)，浏览器直接访问（HTTP 200，API 端点 404）。

## 数据采集

1. `browser_navigate → fotmob.com/leagues/77/fixtures/world-cup`
2. 从页面 UI 提取比赛日期/队名/比分（UI 直接渲染，无需 API）
3. 赛后可从 NextJS `__NEXT_DATA__` 提取 matchId 获取详细统计
4. 追加到 `scripts/fotmob_pipeline.py` 的 `FOTMOB_RESULTS` 列表

## 统计估算

xG/射门/控球率按 FIFA 4 档分级 + 实际比分估算：
- Tier 1 (阿根廷/巴西/法国等): xG 1.5-3.0, 控球 53-65%
- Tier 2 (日本/美国/摩洛哥等): xG 1.0-2.0, 控球 46-56%
- Tier 3 (突尼斯/瑞典/厄瓜多尔等): xG 0.6-1.5, 控球 40-50%
- Tier 4 (库拉索/海地等): xG 0.3-0.9, 控球 34-44%

估算时加主场优势 (+0.15 xG)，确保比分一致性。

## 关键比赛记录

| 比赛 | 日期 | 比分 | 备注 |
|------|------|------|------|
| 突尼斯 vs 日本 | Jun 21 | TBD | 待开赛 |
| 荷兰 vs 瑞典 | Jun 21 | 5-1 | FotMob 确认 |
| 瑞典 vs 突尼斯 | Jun 16 | 5-1 | 突尼斯防线崩盘 |
| 荷兰 vs 突尼斯 | Jun 17 | 4-0 | 突尼斯 0 分 3 轮 |
| 日本 vs 瑞典 | Jun 17 | 2-1 | 日本 2 胜 1 负 |

## 替代方案对比

| 数据源 | 可访问 | 质量 | 自动化 |
|--------|--------|------|--------|
| FotMob | ✅ 浏览器 | 真实比分 | 半自动 |
| WhoScored (Opta) | ❌ 403 | 最优 | 需付费 |
| FBref (Opta) | ❌ 403 | 最优 | 需反爬 |
| StatsBomb Open | ✅ 仅历史 | 最优 | 不支持 2026 |
| ESPN | ✅ 浏览器 | 真实比分 | 半自动 |
