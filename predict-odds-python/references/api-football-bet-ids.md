# api-football Bet365 Bet IDs 速查

常用盘口类型及对应 Bet365 bet ID。用于从 odds 端点精确提取目标盘口。

## 核心盘口（每次分析必拉）

| ID | 名称 | 用途 |
|----|------|------|
| 1 | Match Winner | 胜平负 (Home/Draw/Away) |
| 5 | Goals Over/Under | 大小球 (多线：0.5/1.5/2.5/3.5...) |
| 8 | Both Teams Score | 双方进球 (Yes/No) |
| 10 | Exact Score | 精确比分 (1:0, 2:0, 2:1, 0:0, 1:1...) |

## 角球盘口（Corners）

| ID | 名称 | 说明 |
|----|------|------|
| **45** | Corners Over Under | 总角球大小 (8.5/9.5 线) |
| 56 | Corners Asian Handicap | 角球亚盘 (Home -2/Away -2) |
| 57 | Home Corners Over/Under | 主队角球大小 |
| 58 | Away Corners Over/Under | 客队角球大小 |
| 77 | Total Corners (1st Half) | 上半场角球 |
| 85 | Total Corners (3 way) | 总角球精确区间 (Exactly 8/Over 8/Under 8...) |
| 239 | Corners European Handicap | 角球欧盘 |
| 247 | Corners Race To | 先到 N 角 |
| 249 | Multicorners | 多角球组合 |
| 295 | Corners. Total (Range) | 角球区间 |

## 半场盘口

| ID | 名称 |
|----|------|
| 13 | First Half Winner |
| 18 | Handicap Result - First Half |
| 19 | Asian Handicap First Half |
| 31 | Correct Score - First Half |
| 34 | Both Teams Score - First Half |

## 其他有用盘口

| ID | 名称 | 用途 |
|----|------|------|
| 11 | Highest Scoring Half | 哪半场进球多 |
| 12 | Double Chance | 双重机会 (HomeDraw/DrawAway/HomeAway) |
| 14 | Team To Score First | 先进球 |
| 15 | Team To Score Last | 最后进球 |
| 80 | Cards Over/Under | 总牌数 |

## 用法

```bash
curl -s "https://v3.football.api-sports.io/odds?fixture=FID&bookmaker=8" \
  -H "x-apisports-key: $KEY" | python3 -c "
import json,sys; d=json.load(sys.stdin)
for odd in d.get('response',[]):
    for bet in odd.get('bookmakers',[{}])[0].get('bets',[]):
        if bet.get('id') in [1,5,10,45,8]:
            n=bet.get('name','?')
            v=' | '.join([f\"{x.get('value','?')}:{x.get('odd','?')}\" for x in bet.get('values',[])])
            print(f'{n}: {v}')
"
```

⚠️ Bet365 不一定为所有比赛提供角球盘口——强弱过于悬殊或开赛前的低关注度比赛可能只有基础盘口 (1/5/8)。
