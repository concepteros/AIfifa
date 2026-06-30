#!/usr/bin/env python3
"""Search Predict.fun for match-specific markets."""
import json, os
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from predict_odds.env_loader import load_env_file
load_env_file('/Users/macbook/AIfifa/predict-odds-python/.env')

API_KEY = os.environ['PREDICTFUN_API_KEY']
HEADERS = {'x-api-key': API_KEY, 'User-Agent': 'predictfun-cli/1.0', 'Accept': 'application/json'}

BASE = 'https://api.predict.fun'

def req(path):
    url = f'{BASE}{path}'
    r = Request(url, headers=HEADERS)
    try:
        with urlopen(r, timeout=15) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        body = e.read().decode()
        return {'error': str(e), 'body': body[:500]}

# Try markets endpoint with search
for query in ['fifwc', 'tunisia', 'japan', 'world cup match', 'fifa world cup 2026', 'match']:
    data = req(f'/v1/markets?search={query.replace(" ", "%20")}')
    markets = data.get('data', [])
    cursor = data.get('cursor', 'none')
    print(f'\n=== search="{query}" => {len(markets)} markets, cursor={cursor} ===')
    for m in markets[:3]:
        mid = m.get('id')
        slug = m.get('categorySlug', '')
        q = m.get('question', '')[:120]
        print(f'  #{mid} slug={slug}')
        print(f'    Q: {q}')
        for o in m.get('outcomes', []):
            name = o.get('name','')
            ask = o.get('bestAsk')
            bid = o.get('bestBid')
            ap = ask.get('price') if isinstance(ask, dict) else ask
            bp = bid.get('price') if isinstance(bid, dict) else bid
            print(f'    {name}: ask={ap} bid={bp}')
