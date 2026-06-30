import json

with open('/Users/macbook/AIfifa/predict-odds-python/data/bot-scan.json') as f:
    config = json.load(f)

config['scan']['date'] = '2026-06-29'

with open('/Users/macbook/AIfifa/predict-odds-python/data/bot-scan.json', 'w') as f:
    json.dump(config, f, indent=2)

print("Updated scan date to 2026-06-29 (UTC)")
