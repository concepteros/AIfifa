import json, sys, urllib.request

url = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates=20260630"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read())

events = data.get('events', [])
print(f'Total events on 2026-06-30 (UTC): {len(events)}')
for e in events:
    name = e.get('name', '?')
    status = e.get('status', {}).get('type', {}).get('name', '?')
    date = e.get('date', '?')
    print(f'  {name} | {status} | {date}')
    for comp in e.get('competitions', []):
        for team in comp.get('competitors', []):
            print(f'    {team["team"]["displayName"]}: {team.get("score", "?")}')
