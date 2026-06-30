#!/usr/bin/env python3
"""Get specific markets and check orderbook."""
import json, os
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from predict_odds.env_loader import load_env_file
load_env_file('/Users/macbook/AIfifa/predict-odds-python/.env')

API_KEY=*** '')
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

# Try specific market
for mid in [163340, 542513, 534660]:
    data = req(f'/v1/markets/{mid}')
    m = data.get('data', data)
    if 'error' not in m:
        print(f'\n=== Market #{mid} ===')
        print(f'slug: {m.get("categorySlug","")}')
        print(f'Q: {m.get("question","")[:120]}')
        for o in m.get('outcomes', []):
            name = o.get('name','')
            ask = o.get('bestAsk')
            bid = o.get('bestBid')
            ap = ask.get('price') if isinstance(ask, dict) else ask
            bp = bid.get('price') if isinstance(bid, dict) else bid
            print(f'  {name}: ask={ap} bid={bp}')
    else:
        print(f'\nMarket #{mid}: {data}')

# Also try active event with match slugs
data = req('/v1/categories')
events = data.get('data', [])
for e in events:
    slug = e.get('categorySlug', '')
    title = e.get('title', '')
    if 'match' in slug.lower() or 'world' in title.lower():
        print(f'\nEvent #{e.get("id")} slug={slug}: {title[:80]}')
        for m in e.get('markets', [])[:3]:
            print(f'  Market #{m.get("id")} slug={m.get("categorySlug","")}: {m.get("question","")[:80]}')
