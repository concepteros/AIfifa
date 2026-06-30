#!/usr/bin/env python3
"""Quick check of Predict.fun categories to find World Cup markets."""
import json, os
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# Load env
for line in open('.env'):
    line = line.strip()
    if not line or line.startswith('#') or '=' not in line:
        continue
    k, v = line.split('=', 1)
    k = k.strip()
    if k not in os.environ:
        os.environ[k] = v.strip().strip('"').strip("'")

API_KEY = os.environ.get('PREDICTFUN_API_KEY', '')
HEADERS = {'x-api-key': API_KEY, 'User-Agent': 'predictfun-cli/1.0', 'Accept': 'application/json'}

def req(path):
    url = f'https://api.predict.fun{path}'
    r = Request(url, headers=HEADERS)
    try:
        with urlopen(r, timeout=15) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        body = e.read().decode()
        return {'error': str(e), 'body': body[:500]}

data = req('/v1/categories')
events = data.get('data', [])
print(f'Total events: {len(events)}')

# Print ALL events with their slugs to understand structure
for e in events:
    eid = e.get('id')
    slug = e.get('categorySlug', '')
    title = e.get('title', '')[:80]
    status = e.get('status', '')
    mcount = len(e.get('markets', []))
    print(f'  #{eid} [{status}] slug={slug} markets={mcount}')
    print(f'    {title}')
    for m in e.get('markets', []):
        mid = m.get('id')
        mslug = m.get('categorySlug', '')
        q = m.get('question', '')[:100]
        print(f'    Market #{mid} slug={mslug}')
        print(f'      Q: {q}')
        for o in m.get('outcomes', []):
            print(f'      {o["name"]}: ask={o.get("bestAsk")} bid={o.get("bestBid")}')
    print()
