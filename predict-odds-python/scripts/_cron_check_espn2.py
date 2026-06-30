import json, urllib.request
from datetime import datetime, timezone, timedelta

# Check June 29 and June 30 UTC for BJT June 30 matches
for date_str in ['20260629', '20260630']:
    url = f'https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates={date_str}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    events = data.get('events', [])
    print(f'\n--- {date_str} UTC ({len(events)} events) ---')
    for e in events:
        name = e.get('name', '?')
        dt = e.get('date', '?')
        status = e.get('status', {}).get('type', {}).get('name', '?')
        if dt.endswith('Z'):
            utc_time = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            bjt_time = utc_time + timedelta(hours=8)
            bjt_date = bjt_time.strftime('%Y-%m-%d')
            print(f'  {name}: UTC={dt} BJT={bjt_time.strftime("%Y-%m-%d %H:%M")} → BJT day={bjt_date} [{status}]')
        else:
            print(f'  {name}: {dt} [{status}]')
