import json, urllib.request, os
from dotenv import load_dotenv

load_dotenv('/Users/macbook/AIfifa/predict-odds-python/.env')
api_key = os.getenv('API_FOOTBALL_KEY')

# First, find the fixture for Morocco vs Netherlands on 2026-06-29
url = "https://v3.football.api-sports.io/fixtures?date=2026-06-29"
req = urllib.request.Request(url, headers={
    'x-apisports-key': api_key,
    'User-Agent': 'Mozilla/5.0'
})

with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read())

fixtures = data.get('response', [])
print(f"Total fixtures on 2026-06-29: {len(fixtures)}")

for f in fixtures:
    fixture_id = f['fixture']['id']
    home = f['teams']['home']['name']
    away = f['teams']['away']['name']
    date = f['fixture']['date']
    status = f['fixture']['status']['long']
    print(f"\n  [{fixture_id}] {home} vs {away}")
    print(f"  Date: {date} | Status: {status}")

# Also check June 30 for completeness
url2 = "https://v3.football.api-sports.io/fixtures?date=2026-06-30"
req2 = urllib.request.Request(url2, headers={
    'x-apisports-key': api_key,
    'User-Agent': 'Mozilla/5.0'
})
with urllib.request.urlopen(req2) as resp2:
    data2 = json.loads(resp2.read())
fixtures2 = data2.get('response', [])
print(f"\n\nTotal fixtures on 2026-06-30: {len(fixtures2)}")
for f in fixtures2:
    fixture_id = f['fixture']['id']
    home = f['teams']['home']['name']
    away = f['teams']['away']['name']
    date = f['fixture']['date']
    status = f['fixture']['status']['long']
    print(f"  [{fixture_id}] {home} vs {away} | {date} | {status}")
