# 名气溢价 (Star Premium) 投注模式

> 2026-06-23 发现：Norway (FIFA #44) 让 Senegal (FIFA #20) 球，原因只有一个——Haaland。

## 模式定义

当市场因单个超级球星将弱队推为让球方或严重高估时，形成**名气溢价 (Star Premium)**。

**条件：**
- FIFA 排名差 ≥ 10 位（高排位队反而受让）
- 低排位队拥有 Haaland/Salah/Mbappe 级别球星
- 高排位队是洲际冠军/世界杯常客

## 案例：Norway vs Senegal (2026-06-23)

| 指标 | Norway | Senegal |
|------|--------|---------|
| FIFA 排名 | #44 | #20 |
| Bet365 ML | 2.15 (让球) | 3.30 |
| 大赛经验 | 数十年首次世界杯 | 2022年淘汰赛+非洲冠军 |
| 战术模型 | possession 4-3-3 | high_press 4-3-3 |
| 战术评分 | 被压制 | **-0.12 客场优势** |

**市场逻辑**：Haaland = 进球 = Norway 该赢 → 2.15 让球
**实际情况**：Senegal 更强（排名、经验、战术对位），但 Haaland 名气把 Norway 推到了不该在的位置

**投注**：Senegal +0.5 AH @~1.85 ✅

## 识别方法

```python
# 伪代码：检测名气溢价
def detect_star_premium(match):
    home_rank, away_rank = get_fifa_ranks(match)
    home_ml, away_ml = get_bet365_odds(match)
    star_players = get_key_players(match)  # from tactics.py
    
    rank_diff = away_rank - home_rank  # 正=客更强
    
    if rank_diff > 10 and home_ml < 3.0:
        # 主队更弱但让球 → 检查是否有超级球星
        for p in star_players:
            if p in ['Haaland', 'Salah', 'Mbappe', 'Vinicius Jr']:
                return True, f"Star premium: {p} (FIFA #{home_rank}) favored over #{away_rank}"
    return False, None
```

## 超级球星名单（World Cup 2026）

触发名气溢价的球员层级：
- **Tier 1（铁定触发）**：Haaland, Mbappe, Vinicius Jr, Salah
- **Tier 2（可能触发）**：Musiala, Bellingham, Pedri, Yamal, Valverde
- **Tier 3（微幅影响）**：其他球队核心

## 投注策略

| 场景 | 操作 |
|------|------|
| 名气溢价确认 | **高排名队 +0.5 AH**（受让方） |
| 溢价 + BTTS Yes < 1.80 | BTTS Yes 有价值（明星前锋=市场预期双方进球） |
| 溢价 + 对手洲际冠军 | 加大对手投注（经验差+名气差双杀） |

## 🔴 反例：Norway 3-2 Senegal (2026-06-23 验证)

**预测**：Senegal ML @3.30（名气溢价假说）→ 结果 Norway 3-2 胜

**失败原因**：Haaland 确实打爆了比赛。名气溢价假说假设市场被 Haaland 名字拉偏，但实际上 Haaland 的能力配得上这个定价——他真能靠个人能力赢球。

**修正后的识别条件**：
1. 超级球星 + 弱队体系 ≠ 自动溢价。需要判断：球星是"仅有的武器"还是"能带飞全队"
2. 如果弱队整体战术围绕球星构建（如 Norway 4-3-3 以 Haaland 为支点），溢价可能是真实的
3. 如果球星孤悬于体系之外（如 Salah 在埃及的孤立感），溢价才是虚假的
4. **关键区分**：球星所在队的首轮表现——如果首轮已展示攻击力（Norway 首轮？），溢价可信

## 局限性

- 超级球星确实可能靠个人能力改变比赛——**Norway 3-2 Senegal 已证明此点**
- 溢价真假需要看首轮表现验证：首轮爆发的溢价=真实，首轮沉寂的溢价=虚假
- 只适用于小组赛——淘汰赛紧张度降低名气溢价效应
- 需要确认球星健康（伤病时溢价自动消失）
- **新的安全阀**：不要仅凭FIFA排名差+球星名字就下注对手。先检查球星首轮数据（进球/xG/射正）
