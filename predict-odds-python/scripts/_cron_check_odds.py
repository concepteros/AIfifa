import json, sys, os
from dotenv import load_dotenv

load_dotenv('/Users/macbook/AIfifa/predict-odds-python/.env')

from predict_odds.the_odds_api import TheOddsAPIClient

client = TheOddsAPIClient.from_env()

# Try both dates
for date_str in ['2026-06-29', '2026-06-30']:
    print(f'\n=== The Odds API: {date_str} ===')
    try:
        odds = client.get_odds(
            sport="soccer_fifa_world_cup",
            regions="eu",
            markets=["h2h", "totals", "spreads"],
        )
        # Filter by commence_time
        matches = odds.get('data', odds) if isinstance(odds, dict) else []
        if isinstance(matches, list):
            print(f'  Total matches returned: {len(matches)}')
            for m in matches[:5]:
                name = f"{m.get('home_team', '?')} vs {m.get('away_team', '?')}"
                ct = m.get('commence_time', 'N/A')
                print(f'  {name} | {ct}')
        else:
            print(f'  Response type: {type(matches)}')
    except Exception as e:
        print(f'  Error: {e}')
