import unittest

from predict_odds.market_sources import (
    fetch_market_events,
    merge_normalized_events,
    normalize_polymarket_markets,
    predict_fun_response_to_events,
)
from predict_odds.models import FootballOddsResponse, OddsMarket, Outcome


class MarketSourcesTest(unittest.TestCase):
    def test_fetches_configured_sources_and_merges_them(self):
        config = {
            "odds_sources": ["the_odds_api", "predict_fun", "polymarket"],
            "scan": {
                "sport": "soccer_epl",
                "regions": "eu",
                "markets": ["h2h"],
                "league": "Premier League",
                "date": "2026-06-20",
            },
            "polymarket": {"query": "Arsenal Chelsea", "limit": 20},
        }
        clients = {
            "the_odds_api": _FakeTheOddsAPIClient(),
            "predict_fun": _FakePredictFunClient(),
            "polymarket": _FakePolymarketClient(),
        }

        events = fetch_market_events(config, clients=clients)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["home_team"], "Arsenal")
        self.assertEqual(events[0]["markets"]["home_win"], 2.2)
        self.assertEqual(events[0]["markets"]["draw"], 3.4)
        self.assertEqual(events[0]["sources"], ["the_odds_api", "predict_fun", "polymarket"])
        self.assertEqual(clients["the_odds_api"].seen["sport"], "soccer_epl")
        self.assertEqual(clients["predict_fun"].seen["league"], "Premier League")
        self.assertEqual(clients["polymarket"].seen["query"], "Arsenal Chelsea")

    def test_fetch_keeps_working_when_one_source_fails(self):
        config = {
            "odds_sources": ["the_odds_api", "predict_fun"],
            "scan": {"sport": "soccer_epl", "regions": "eu", "markets": ["h2h"], "league": "Premier League", "date": "2026-06-20"},
        }
        clients = {"the_odds_api": _BrokenClient(), "predict_fun": _FakePredictFunClient()}

        events = fetch_market_events(config, clients=clients)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["sources"], ["predict_fun"])

    def test_merges_sources_and_uses_best_price_per_market(self):
        events = merge_normalized_events(
            [
                {
                    "event_id": "odds-1",
                    "home_team": "Arsenal",
                    "away_team": "Chelsea",
                    "commence_time": "2026-06-20T19:00:00Z",
                    "markets": {"home_win": 2.1, "draw": 3.4},
                    "sources": ["the_odds_api"],
                },
                {
                    "event_id": "predict-1",
                    "home_team": "Arsenal",
                    "away_team": "Chelsea",
                    "commence_time": "2026-06-20T19:00:00Z",
                    "markets": {"home_win": 2.25, "away_win": 3.0},
                    "sources": ["predict_fun"],
                },
                {
                    "event_id": "poly-1",
                    "home_team": "Arsenal",
                    "away_team": "Chelsea",
                    "commence_time": "2026-06-20T19:00:00Z",
                    "markets": {"home_win": 2.05, "over_2_5": 1.9},
                    "sources": ["polymarket"],
                },
            ]
        )

        self.assertEqual(len(events), 1)
        merged = events[0]
        self.assertEqual(merged["event_id"], "odds-1+predict-1+poly-1")
        self.assertEqual(merged["markets"]["home_win"], 2.25)
        self.assertEqual(merged["markets"]["draw"], 3.4)
        self.assertEqual(merged["markets"]["away_win"], 3.0)
        self.assertEqual(merged["markets"]["over_2_5"], 1.9)
        self.assertEqual(merged["sources"], ["the_odds_api", "predict_fun", "polymarket"])

    def test_converts_predict_fun_grouped_markets_to_events(self):
        response = FootballOddsResponse(
            league="Premier League",
            date="2026-06-20",
            source="https://api.predict.fun/v1/markets",
            fetched_at="2026-06-20T00:00:00Z",
            raw_count=1,
            markets={
                "win_draw_win": [
                    OddsMarket(
                        market_id="pf-1",
                        market_type="win_draw_win",
                        match_id="match-1",
                        home_team="Arsenal",
                        away_team="Chelsea",
                        kickoff="2026-06-20T19:00:00Z",
                        outcomes=[
                            Outcome(name="Arsenal", odds=2.2),
                            Outcome(name="Draw", odds=3.5),
                            Outcome(name="Chelsea", odds=3.1),
                        ],
                    )
                ],
                "totals": [
                    OddsMarket(
                        market_id="pf-2",
                        market_type="totals",
                        match_id="match-1",
                        home_team="Arsenal",
                        away_team="Chelsea",
                        kickoff="2026-06-20T19:00:00Z",
                        outcomes=[Outcome(name="Over", odds=1.88, line=2.5)],
                    )
                ],
            },
        )

        events = predict_fun_response_to_events(response)

        self.assertEqual(events[0]["event_id"], "predict_fun:match-1")
        self.assertEqual(events[0]["markets"]["home_win"], 2.2)
        self.assertEqual(events[0]["markets"]["draw"], 3.5)
        self.assertEqual(events[0]["markets"]["away_win"], 3.1)
        self.assertEqual(events[0]["markets"]["over_2_5"], 1.88)
        self.assertEqual(events[0]["sources"], ["predict_fun"])

    def test_normalizes_polymarket_decimal_prices(self):
        markets = [
            {
                "id": "poly-1",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "commence_time": "2026-06-20T19:00:00Z",
                "outcomes": ["Arsenal", "Draw", "Chelsea"],
                "outcomePrices": ["0.48", "0.27", "0.25"],
            }
        ]

        events = normalize_polymarket_markets(markets)

        self.assertEqual(events[0]["event_id"], "polymarket:poly-1")
        self.assertEqual(events[0]["markets"]["home_win"], 2.083333)
        self.assertEqual(events[0]["markets"]["draw"], 3.703704)
        self.assertEqual(events[0]["markets"]["away_win"], 4.0)
        self.assertEqual(events[0]["sources"], ["polymarket"])


class _FakeTheOddsAPIClient:
    def __init__(self):
        self.seen = {}

    def get_odds(self, **kwargs):
        self.seen = kwargs
        return [
            {
                "id": "odds-1",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "commence_time": "2026-06-20T19:00:00Z",
                "bookmakers": [
                    {
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {"name": "Arsenal", "price": 2.1},
                                    {"name": "Draw", "price": 3.4},
                                    {"name": "Chelsea", "price": 3.0},
                                ],
                            }
                        ]
                    }
                ],
            }
        ]


class _FakePredictFunClient:
    def __init__(self):
        self.seen = {}

    def get_football_odds(self, **kwargs):
        self.seen = kwargs
        return FootballOddsResponse(
            league=kwargs["league"],
            date=kwargs["date"],
            source="https://api.predict.fun/v1/markets",
            fetched_at="2026-06-20T00:00:00Z",
            raw_count=1,
            markets={
                "win_draw_win": [
                    OddsMarket(
                        market_id="pf-1",
                        market_type="win_draw_win",
                        match_id="match-1",
                        home_team="Arsenal",
                        away_team="Chelsea",
                        kickoff="2026-06-20T19:00:00Z",
                        outcomes=[Outcome(name="Arsenal", odds=2.2)],
                    )
                ]
            },
        )


class _FakePolymarketClient:
    def __init__(self):
        self.seen = {}

    def get_markets(self, **kwargs):
        self.seen = kwargs
        return [
            {
                "id": "poly-1",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "commence_time": "2026-06-20T19:00:00Z",
                "outcomes": ["Arsenal"],
                "outcomePrices": ["0.5"],
            }
        ]


class _BrokenClient:
    def get_odds(self, **kwargs):
        raise RuntimeError("source down")


if __name__ == "__main__":
    unittest.main()
