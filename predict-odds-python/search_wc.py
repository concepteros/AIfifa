#!/usr/bin/env python3
"""Try Predict.fun search for World Cup."""
import json, os
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# Load env carefully
for line in open('/Users/macbook/AIfifa/predict-odds-python/.env'):
    line = line.strip()
    if not line or line.startswith('#') or '=' not in line:
        continue
    k, v = line.split('=', 1)
    k = k.strip()
    if k not in os.environ:
        os.environ[k] = v.strip().strip('"').strip("'")

API_KEY = os.environ.get('PREDICTFUN_API_KEY', '')
HEADERS = {'x-api-key': API_KEY, 'User-Agent': 'predictfun-cli/1.0', 'Accept': 'application/json'}

url = 'https://api.predict.fun/v1/search?query=world+cup'
r = Request(url, headers=HEADERS)
try:
    with urlopen(r, timeout=15) as resp:
        data = json.loads(resp.read())
    print(json.dumps(data, indent=2)[:5000])
except HTTPError as e:
    body = e.read().decode()
    print(f'HTTP {e.code}: {body[:500]}')
