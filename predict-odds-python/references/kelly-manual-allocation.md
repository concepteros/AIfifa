# 手动 Kelly 多场全盘口分配流程

当用户要求「用 Kelly 给 $X 仓位分配，每场含 ML+大小球+角球+波胆」时的完整操作流程。

## 适用触发

- "用凯利公式给 $X 仓位下法"
- "每场押 ML + 大小球 + 角球 + 一个比分"
- 手工多场跨盘口批量下注

## 六步流程

### Step 1: 拉 ESPN 确定赛程

```bash
for d in 20260622 20260623; do
  curl -s "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates=$d" \
    -H "User-Agent: Mozilla/5.0" | python3 -c "
import json,sys; from datetime import datetime,timezone,timedelta
d=json.load(sys.stdin); bjt=timezone(timedelta(hours=8))
start=datetime(2026,6,23,0,0,0,tzinfo=bjt); end=start.replace(hour=23,minute=59,second=59)
for e in d.get('events',[]):
    c=e.get('competitions',[{}])[0]
    h=c.get('competitors',[{}])[0].get('team',{}).get('displayName','?')
    a=c.get('competitors',[{}])[1].get('team',{}).get('displayName','?')
    dt=datetime.fromisoformat(e.get('date','').replace('Z','+00:00')).astimezone(bjt)
    if start<=dt<=end:
        print(f'{dt.strftime(\"%H:%M\")}|{h}|{a}|{e.get(\"status\",{}).get(\"type\",{}).get(\"name\",\"?\")}'
" 2>&1
done
```

过滤 `STATUS_SCHEDULED` 的场次。

### Step 2: 拉 Bet365 赔率（3类盘口）

对每个 FID 分别拉 odds 端点，提取 bet IDs:
- **1** → 胜平负 (Match Winner)
- **5** → 大小球 (Goals Over/Under)
- **45** → 角球 (Corners Over Under)
- **8** → BTTS
- **10** → 精确比分 (Exact Score)

```bash
curl -s "https://v3.football.api-sports.io/odds?fixture=$FID&bookmaker=8" \
  -H "x-apisports-key: $KEY" | python3 -c "..." 
```

⚠️ **用 curl 直通管道，不要走 execute_code terminal()** —— odds JSON 通常 > 20KB，会在 execute_code 中被截断。

### Step 3: 跑战术+裁判分析

```python
from predict_odds.tactics import get_team_profile, generate_tactical_analysis
from predict_odds.supplementary import get_match_referee, get_match_referee_profile
```

提取：
- 战术对位评分（+/- 优势）
- 风格克制关系
- 关键球员对位
- 裁判严格度/出牌倾向（可小幅调整 λ）

### Step 4: 计算模型概率

不使用 scan 输出（常因队名/日期不匹配返回 0），而是**人工估算**：

```
模型概率 = 市场隐含概率 ± 战术调整 ± 裁判调整 ± 陷阱调整
```

调整规则：
- **战术优势 +0.10**: 主场强队 vs 风格被克制对手 → +5-8pp
- **1.35-1.45 陷阱**: 此区间强队 ML → -10pp（Draw +8pp）
- **Star Premium**: 明星名气让弱队让球 → 高排名队 +5pp
- **严格裁判 (strict > 0.70)**: Under +2pp
- **高 card_tendency (> 0.55)**: Under +1pp
- **模型 vs 市场差距 > 20pp**: 以市场为准
- **差距 < 10pp**: 可信任 Edge

### Step 5: 计算 Kelly 仓位

```python
BANKROLL = 1000
FRACTIONAL = 0.25  # 1/4 Kelly
MAX_SINGLE = {bankroll * 0.05}  # 单注上限 5%

def kelly(prob, decimal_odds):
    b = decimal_odds - 1
    if b <= 0: return 0
    q = 1 - prob
    return max(0, (b * prob - q) / b)

def stake(prob, decimal_odds):
    f = kelly(prob, decimal_odds)
    return min(BANKROLL * f * FRACTIONAL, MAX_SINGLE)
```

输出格式：
```
投注项    模型概率  市场隐含  赔率  Kelly全  1/4仓位  状态
```

**只有 Kelly > 0 的才下注**。Edge 为负的盘口直接标 ❌ 跳过。

### Step 6: 波胆选择

从 Bet365 Exact Score 列表中取**模型认为最可能且 Edge > 0** 的比分：

1. 市场最低赔率的比分（最可能）→ 检查是否与战术分析一致
2. Under 2.5 场 → 1-0 / 2-0 / 0-1
3. 对攻场 → 2-1 / 1-2 / 2-2 / 1-1
4. 碾压场 → 3-0 / 4-0

波胆不按标准 Kelly 公式（样本太小），用简化版：
```
波胆仓位 = $50 * (模型概率 - 市场隐含概率)  # 正 Edge 才投
等于：edge_pp / 100 * MAX_SINGLE
```

## 输出模板

```
💰 $X Kelly仓位分配

⚽ ① Home vs Away (HH:MM BJT)
| # | 盘口 | 赔率 | 市场隐含 | 模型概率 | Kelly | 仓位 |
|---|------|------|---------|---------|-------|------|

📊 总仓位汇总
| 场次 | 胜平负 | 大小球 | 角球 | 波胆 | 小计 |
```

## 已知陷阱

1. **不要用 scan 的自动 Kelly 输出** — scan 常因队名不匹配返回 0 结果
2. **fbref.csv 数据为合成** — 不能用作模型概率的 λ 校准源
3. **弱队（未收录于 tactics DB）无战术分析** — 标注「未入库」，不强行分析
4. **个别比赛 Bet365 无角球盘口** — 标注「*估算」，不捏造数据
5. **execute_code terminal() 截断大 JSON** — 永远 curl | python3 直通
