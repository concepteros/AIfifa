#!/usr/bin/env python3
"""Search Predict.fun for match-specific markets."""
import json, os
from urllib.request import Request, urlopen
from urllib.error import HTTPError

for line in open('/Users/macbook/AIfifa/predict-odds-python/.env'):
    line = line.strip()
    if not line or line.startswith('#') or '=' not in line:
        continue
    k, v = line.split('=', 1)
    k = k.strip()
    if k not in os.environ:
        os.environ[k] = v.strip().strip('"').strip("'")

API_KEY=os.env...EY', '')
HEADERS = {'x-api-key': API_KEY, 'User-Agent': 'predictfun-cli/1.0', 'Accept': 'application/json'}

# Try markets endpoint with search
for query in ['fifwc', 'tunisia', 'japan', 'world cup match', 'fifa world cup 2026']:
    url = f'https://api.predict.fun/v1/markets?search={query.replace(" ", "%20")}'
    r = Request(url, headers=HEADERS)
    try:
        with urlopen(r, timeout=15) as resp:
            data = json.loads(resp.read())
        markets = data.get('data', [])
        cursor = data.get('cursor', 'none')
        print(f'\n=== search="{query}" => {len(markets)} markets, cursor={cursor} ===')
        for m in markets[:3]:
            mid = m.get('id')
            slug = m.get('categorySlug', '')
            q = m.get('question', '')[:100]
            print(f'  #{mid} slug={slug}')
            print(f'    Q: {q}')
            for o in m.get('outcomes', []):
                name = o.get('name','')
                ask = o.get('bestAsk')
                bid = o.get('bestBid')
                ap = ask.get('price') if isinstance(ask, dict) else ask
                bp = bid.get('price') if isinstance(bid, dict) else bid
                print(f'    {name}: ask={ap} bid={bp}')
    except HTTPError as e:
        body = e.read().decode()
        print(f'HTTP {e.code}: {body[:300]}')
