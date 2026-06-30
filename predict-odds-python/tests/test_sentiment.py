import json
import unittest
from unittest.mock import patch

from predict_odds.aliases import TeamAliasResolver
from predict_odds.cli import main
from predict_odds.sentiment import (
    MatchSentiment,
    _clamp_score,
    _score_team_articles,
    analyze_match_sentiment,
    fetch_web_news,
    score_articles,
)


_POS_ARTICLES = [
    {
        "title": "Tunisia win in dominant fashion",
        "text": "Tunisia produced a superb victory, thrashing their opponents with confidence.",
        "source": "test",
    },
    {
        "title": "Tunisia in excellent form ahead of clash",
        "text": "The team is flying and looks unstoppable.",
        "source": "test",
    },
]

_NEG_ARTICLES = [
    {
        "title": "Japan suffer defeat in shock upset",
        "text": "Japan lost and looked weak throughout the match.",
        "source": "test",
    },
    {
        "title": "Japan injury crisis deepens",
        "text": "Another key player is out with injury, dealing a major blow.",
        "source": "test",
    },
]

_MIXED_ARTICLES = [
    {
        "title": "Tunisia win but concerns remain",
        "text": "Victory came at a cost with two injuries.",
        "source": "test",
    },
    {
        "title": "Japan lose but show promise",
        "text": "Despite the defeat, there were positive signs.",
        "source": "test",
    },
]


class SentimentScoringTests(unittest.TestCase):
    def test_positive_articles_score_above_zero(self):
        score, sources = _score_team_articles(_POS_ARTICLES, "Tunisia")
        self.assertGreater(score, 0.0)
        self.assertIn("test", sources)

    def test_negative_articles_score_below_zero(self):
        score, sources = _score_team_articles(_NEG_ARTICLES, "Japan")
        self.assertLess(score, 0.0)
        self.assertIn("test", sources)

    def test_mixed_articles_score_near_zero(self):
        score, _ = _score_team_articles(_MIXED_ARTICLES, "Tunisia")
        # Mixed positive/negative should be near zero
        self.assertGreaterEqual(score, -0.5)
        self.assertLessEqual(score, 0.5)

    def test_empty_articles_returns_zero(self):
        score, sources = _score_team_articles([], "AnyTeam")
        self.assertEqual(score, 0.0)
        self.assertEqual(sources, [])

    def test_articles_without_text_return_zero(self):
        score, _ = _score_team_articles(
            [{"title": "", "text": "", "source": "x"}], "Team"
        )
        self.assertEqual(score, 0.0)

    def test_clamp_score(self):
        self.assertEqual(_clamp_score(1.5), 1.0)
        self.assertEqual(_clamp_score(-1.5), -1.0)
        self.assertEqual(_clamp_score(0.75), 0.75)
        self.assertEqual(_clamp_score(-0.3), -0.3)

    def test_score_articles_public_api(self):
        score, sources = score_articles(_POS_ARTICLES, "Tunisia")
        self.assertGreater(score, 0.0)


class AnalyzeMatchSentimentTests(unittest.TestCase):
    def test_with_prefetched_articles(self):
        articles = _POS_ARTICLES + _NEG_ARTICLES + [
            {"title": "Neutral background info", "text": "The match will be played.", "source": "test"},
        ]
        result = analyze_match_sentiment(
            "Tunisia", "Japan", articles=articles
        )
        self.assertIsInstance(result, MatchSentiment)
        self.assertEqual(result.home_team, "Tunisia")
        self.assertEqual(result.away_team, "Japan")
        # Tunisia articles are positive => score > 0
        self.assertGreater(result.home_sentiment, 0.0)
        # Japan articles are negative => score < 0
        self.assertLess(result.away_sentiment, 0.0)
        self.assertIn("test", result.sources)
        self.assertIsInstance(result.summary, str)
        self.assertGreater(len(result.summary), 0)

    def test_with_alias_resolver(self):
        aliases = TeamAliasResolver({"Tunisia": ["TUN", "Eagles of Carthage"]})
        articles = _POS_ARTICLES + _NEG_ARTICLES + [
            {"title": "neutral", "text": "neutral text", "source": "test"},
        ]
        result = analyze_match_sentiment(
            "Eagles of Carthage", "Japan", alias_resolver=aliases, articles=articles
        )
        self.assertEqual(result.home_team, "Tunisia")

    def test_no_articles_returns_neutral(self):
        result = analyze_match_sentiment("TeamA", "TeamB", articles=[])
        self.assertEqual(result.home_sentiment, 0.0)
        self.assertEqual(result.away_sentiment, 0.0)

    def test_with_mock_fetcher(self):
        def mock_fetch(query: str) -> list[dict[str, str]]:
            if "Argentina" in query:
                return _POS_ARTICLES
            if "Brazil" in query:
                return _NEG_ARTICLES
            return []

        result = analyze_match_sentiment(
            "Argentina", "Brazil", fetch_news=mock_fetch
        )
        self.assertGreater(result.home_sentiment, 0.0)
        self.assertLess(result.away_sentiment, 0.0)

    def test_articles_filtered_by_team(self):
        # Articles that mention only one team should not affect the other
        articles = _POS_ARTICLES + _NEG_ARTICLES + [
            {"title": "neutral", "text": "neutral", "source": "test"},
        ]
        result = analyze_match_sentiment("Tunisia", "Japan", articles=articles)
        # Tunisia gets POS articles, Japan gets NEG articles
        self.assertGreater(result.home_sentiment, 0.0)
        self.assertLess(result.away_sentiment, 0.0)


class FetchWebNewsTests(unittest.TestCase):
    @patch("predict_odds.sentiment._duckduckgo_search")
    def test_fetch_web_news_parses_results(self, mock_search):
        mock_search.return_value = [
            {"title": "Argentina Win World Cup", "text": "Argentina dominated the match.", "source": "web"},
            {"title": "Brazil Injury Blow", "text": "Brazil suffer defeat and injury crisis.", "source": "web"},
        ]
        results = fetch_web_news("football world cup")
        self.assertEqual(len(results), 2)
        self.assertIn("Argentina", results[0]["title"])
        self.assertIn("Brazil", results[1]["title"])

    @patch("predict_odds.sentiment._duckduckgo_search")
    def test_fetch_web_news_handles_error(self, mock_search):
        mock_search.return_value = []
        results = fetch_web_news("football")
        self.assertEqual(results, [])


class CLITests(unittest.TestCase):
    def test_sentiment_command_registered(self):
        result = main(["sentiment", "--match", "fifwc-tun-jpn-2026-06-21", "--no-fetch"])
        # Should succeed (exit 0) even if no articles found
        self.assertEqual(result, 0)

    def test_sentiment_command_with_alias_resolver(self):
        import tempfile, os
        aliases = {"Tunisia": ["TUN"], "Japan": ["JPN"]}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"aliases": aliases}, f)
            alias_path = f.name
        try:
            result = main([
                "sentiment", "--match", "fifwc-tun-jpn-2026-06-21",
                "--alias-file", alias_path,
                "--no-fetch",
            ])
            self.assertEqual(result, 0)
        finally:
            os.unlink(alias_path)

    def test_sentiment_command_with_teams_directly(self):
        result = main([
            "sentiment", "--home-team", "Argentina", "--away-team", "Brazil",
            "--no-fetch",
        ])
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
