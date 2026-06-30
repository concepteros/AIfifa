# Poisson v2 Market Calibration

## 问题
poisson_v1 纯依赖模拟 FBref 数据计算预期进球 λ。模拟数据的 xG 值为随机生成（甚至出现负值），与球队实力无关。导致：
- Spain vs Saudi Arabia: λ_home=0.40 λ_away=0.48 → Spain胜 22.5%，0-0 概率 41.5%
- 市场实际: Spain胜 ~88.5%

## 修复
`poisson_v2` 新增 `_market_implied_lambdas()`:
1. 从胜平负赔率反推市场隐含概率（去水后）
2. 网格搜索最优 (λ_home, λ_away) 使 Poisson 概率与市场概率 MSE 最小
3. 最终 λ = 70% 市场λ + 30% 数据λ

## 参数
| 参数 | 值 | 位置 |
|---|---|---|
| MARKET_WEIGHT | 0.70 | prediction.py |
| LAMBDA_STEP | 0.05 | prediction.py |
| LAMBDA_RANGE | [0.10, 5.00] | prediction.py |
| MAX_GOALS | 6 | prediction.py |

## 调用方式
```python
predict_match(features, odds=markets_dict)
# odds 格式: {"home_win": 1.13, "draw": 11.3, "away_win": 35.0}
```
无 odds 参数时回退到纯数据模式。

## 效果对比（Spain vs Saudi Arabia）
| | v1 数据 | v2 校准 | 市场 |
|---|---|---|---|
| Spain胜 | 22.5% | 79.4% | 88.5% |
| 平 | 49.9% | 15.6% | 8.6% |
| Saudi胜 | 27.6% | 5.7% | 2.9% |
| 大2.5 | 6.0% | 48.9% | ~65% |
