import json, urllib.request, os
from dotenv import load_dotenv

load_dotenv('/Users/macbook/AIfifa/predict-odds-python/.env')
api_key = os.getenv('API_FOOTBALL_KEY')

# Get Netherlands vs Morocco fixture details + league info
url = "https://v3.football.api-sports.io/fixtures?id=1562345"
req = urllib.request.Request(url, headers={
    'x-apisports-key': api_key,
    'User-Agent': 'Mozilla/5.0'
})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read())

f = data['response'][0]
league = f['league']
print(f"League: {league['name']} (id={league['id']})")
print(f"Fixture: {f['fixture']['id']}")
print(f"Date: {f['fixture']['date']}")
print(f"Status: {f['fixture']['status']['long']}")
print(f"Home: {f['teams']['home']['name']}")
print(f"Away: {f['teams']['away']['name']}")
print(f"Venue: {f['fixture']['venue']['name']}, {f['fixture']['venue']['city']}")

# Also check Brazil vs Japan and Germany vs Paraguay scores
for fid in [1562344, 1565176]:
    url2 = f"https://v3.football.api-sports.io/fixtures?id={fid}"
    req2 = urllib.request.Request(url2, headers={
        'x-apisports-key': api_key,
        'User-Agent': 'Mozilla/5.0'
    })
    with urllib.request.urlopen(req2) as resp2:
        d2 = json.loads(resp2.read())
    f2 = d2['response'][0]
    home = f2['teams']['home']['name']
    away = f2['teams']['away']['name']
    hg = f2['goals']['home']
    ag = f2['goals']['away']
    status = f2['fixture']['status']['long']
    print(f"\n{fid}: {home} {hg}-{ag} {away} | {status} | {f2['fixture']['date']}")
