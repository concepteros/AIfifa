"""Sentiment analysis for football matches.

Uses web search and news APIs to gauge public sentiment, recent form,
and key developments for both teams before a match.

When running inside an agent with MCP tools available, the caller can
pass pre-fetched news articles.  In standalone mode the module falls
back to web_search via urllib.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any
from urllib.error import URLError
from urllib.parse import quote_plus, urlencode
from urllib.request import Request, urlopen

from .aliases import TeamAliasResolver

__all__ = [
    "MatchSentiment",
    "analyze_match_sentiment",
    "fetch_web_news",
    "score_articles",
]

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)

# ── sentiment lexicon ────────────────────────────────────────────────
_POSITIVE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bwin\b", r"\bvictory\b", r"\bdominate\b", r"\bdominant\b",
        r"\bstrong\b", r"\bexcellent\b", r"\bsuperb\b", r"\bin.form\b",
        r"\bconfidence\b", r"\bconfident\b", r"\bboost\b", r"\bboosting\b",
        r"\bmomentum\b", r"\bunbeaten\b", r"\bunbeatable\b", r"\bthrash\b",
        r"\brout\b", r"\bimpressive\b", r"\boutstanding\b", r"\bbrilliant\b",
        r"\bstunning\b", r"\bclinical\b", r"\bruthless\b", r"\bflying\b",
        r"\bsoaring\b", r"\bsurging\b", r"\bresurgent\b", r"\brevival\b",
        r"\bcomeback\b", r"\bhero\b", r"\bstar\b", r"\bfit\b(?: again)?\b",
        r"\breturn(?:s|ing)?\b", r"\bhealthy\b", r"\brecovered\b",
        r"\bshutout\b", r"\bclean.sheet\b", r"\bhat.trick\b",
        r"\bqualified\b", r"\badvance\b", r"\bknockout\b",
        r"\btop\b", r"\blead\b", r"\bfavorite\b", r"\bfavourites?\b",
        r"\bchampion\b", r"\btitle\b",
    ]
]

_NEGATIVE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bloss\b", r"\blose\b", r"\blosing\b", r"\blost\b",
        r"\bdefeat\b", r"\bdefeated\b", r"\binjur(?:y|ed|ies)\b",
        r"\bout\b", r"\bdoubt\b", r"\bdoubtful\b", r"\bcrisis\b",
        r"\bpoor\b", r"\bweak\b", r"\bstruggl(?:e|ing|ed)\b",
        r"\bdisappoint(?:ing|ed|ment)?\b", r"\bflop\b", r"\bfail(?:ed|ure)?\b",
        r"\bcrash\b", r"\bslump\b", r"\bsack(?:ed|ing)?\b", r"\bfired?\b",
        r"\bcontroversy\b", r"\bcontroversial\b", r"\bscandal\b",
        r"\bunderperform(?:ing|ed)?\b", r"\bhumiliat(?:ing|ed|ion)\b",
        r"\bworst\b", r"\bterrible\b", r"\bawful\b", r"\bwoeful\b",
        r"\bblunder\b", r"\bhowler\b", r"\bsetback\b", r"\bblow\b",
        r"\bknock\b", r"\bupset\b", r"\bshocks?\b",
        r"\bsuspend(?:ed|sion)\b", r"\bban\b", r"\bbanned\b",
        r"\bred.card\b", r"\bdismissal\b",
        r"\beliminated\b", r"\bknocked.out\b",
    ]
]

_WORLD_CUP_KEYWORDS = [
    "World Cup", "World Cup 2026", "FIFA World Cup", "World Cup match",
    "World Cup preview", "World Cup squad",
]
_INJURY_KEYWORDS = ["injury", "injured", "injury update", "sidelined", "fitness"]
_FORM_KEYWORDS = ["form", "recent results", "last match", "performance"]


@dataclass
class MatchSentiment:
    """Result of a per-match sentiment analysis.

    Attributes:
        home_sentiment: Score between -1.0 (extreme negative) and +1.0 (extreme positive).
        away_sentiment: Score between -1.0 (extreme negative) and +1.0 (extreme positive).
        sources: List of source descriptions that contributed to the analysis.
        summary: Human-readable summary of the sentiment findings.
        home_team: Resolved home team name.
        away_team: Resolved away team name.
    """

    home_team: str
    away_team: str
    home_sentiment: float = 0.0
    away_sentiment: float = 0.0
    sources: list[str] = field(default_factory=list)
    summary: str = ""


def analyze_match_sentiment(
    home_team: str,
    away_team: str,
    *,
    alias_resolver: TeamAliasResolver | None = None,
    articles: Sequence[dict[str, str]] | None = None,
    fetch_news: Callable[[str], list[dict[str, str]]] | None = None,
    timeout: float = 10.0,
) -> MatchSentiment:
    """Analyse public sentiment for a football match.

    Args:
        home_team: Name of the home team.
        away_team: Name of the away team.
        alias_resolver: Optional resolver for team name aliases.
        articles: Pre-fetched news articles (from MCP or other source).
            Each dict should have at least a ``title`` or ``text`` key.
        fetch_news: Callable that takes a search query and returns a list of
            article dicts.  Used as a fallback when ``articles`` is not provided.
        timeout: Timeout for web fetches when using the built-in fetcher.

    Returns:
        MatchSentiment with scores, sources, and a human-readable summary.
    """
    if alias_resolver:
        home_team = alias_resolver.resolve(home_team)
        away_team = alias_resolver.resolve(away_team)

    result = MatchSentiment(home_team=home_team, away_team=away_team)

    # ── gather articles ──────────────────────────────────────────
    if articles is None:
        fetcher = fetch_news or _build_default_fetcher(timeout)
        home_articles = _deduplicate_articles(
            _fetch_team_articles(home_team, fetcher)
        )
        away_articles = _deduplicate_articles(
            _fetch_team_articles(away_team, fetcher)
        )
    else:
        # Split pre-fetched articles by team mention
        home_articles = _filter_team_articles(articles, home_team)
        away_articles = _filter_team_articles(articles, away_team)

    # ── score each side ──────────────────────────────────────────
    home_score, home_srcs = _score_team_articles(home_articles, home_team)
    away_score, away_srcs = _score_team_articles(away_articles, away_team)

    result.home_sentiment = _clamp_score(home_score)
    result.away_sentiment = _clamp_score(away_score)
    result.sources = sorted({*home_srcs, *away_srcs})
    result.summary = _build_summary(home_team, result.home_sentiment,
                                    away_team, result.away_sentiment,
                                    len(home_articles), len(away_articles))

    return result


# ── public helpers ────────────────────────────────────────────────────


def fetch_web_news(
    query: str,
    *,
    timeout: float = 10.0,
    source: str = "web",
) -> list[dict[str, str]]:
    """Fetch news articles from DuckDuckGo (no API key required).

    Args:
        query: Search query string.
        timeout: HTTP request timeout in seconds.
        source: Label attached to each returned article.

    Returns:
        List of article dicts with keys ``title``, ``text``, ``source``.
    """
    return _duckduckgo_search(query, timeout=timeout, source=source)


def score_articles(
    articles: Iterable[dict[str, str]],
    team: str,
) -> tuple[float, list[str]]:
    """Score a collection of articles for sentiment towards *team*.

    Returns (score, sources).
    """
    return _score_team_articles(list(articles), team)


# ── internal scoring ──────────────────────────────────────────────────


def _score_team_articles(
    articles: list[dict[str, str]],
    team: str,
) -> tuple[float, list[str]]:
    if not articles:
        return 0.0, []

    total_score = 0.0
    sources: set[str] = set()
    scored = 0

    for art in articles:
        text = _article_text(art)
        if not text:
            continue
        pos = sum(1 for p in _POSITIVE_PATTERNS if p.search(text))
        neg = sum(1 for p in _NEGATIVE_PATTERNS if p.search(text))
        total = pos + neg
        if total == 0:
            continue
        # Article score in [-1, 1]
        art_score = (pos - neg) / total
        total_score += art_score
        scored += 1
        src = art.get("source", "unknown")
        if src:
            sources.add(src)

    if scored == 0:
        return 0.0, list(sources)
    return total_score / scored, list(sources)


def _clamp_score(value: float) -> float:
    return max(-1.0, min(1.0, round(value, 4)))


def _build_summary(
    home_team: str, home_score: float,
    away_team: str, away_score: float,
    home_count: int, away_count: int,
) -> str:
    def label(score: float) -> str:
        if score > 0.3:
            return "positive"
        if score < -0.3:
            return "negative"
        return "neutral"

    home_label = label(home_score)
    away_label = label(away_score)

    lines = [
        f"{home_team}: sentiment {home_label} ({home_score:+.2f}, {home_count} articles)",
        f"{away_team}: sentiment {away_label} ({away_score:+.2f}, {away_count} articles)",
    ]
    if home_score > away_score + 0.3:
        lines.append(f"Advantage: {home_team}")
    elif away_score > home_score + 0.3:
        lines.append(f"Advantage: {away_team}")
    else:
        lines.append("Sentiment: roughly balanced")
    return " | ".join(lines)


# ── article helpers ───────────────────────────────────────────────────


def _article_text(article: dict[str, str]) -> str:
    """Return the full text to score from an article dict."""
    return article.get("title", "") + " " + article.get("text", "")


def _filter_team_articles(
    articles: Iterable[dict[str, str]],
    team: str,
) -> list[dict[str, str]]:
    """Keep articles that mention *team*."""
    out: list[dict[str, str]] = []
    team_lower = team.casefold()
    for art in articles:
        if team_lower in _article_text(art).casefold():
            out.append(art)
    return out


def _deduplicate_articles(
    articles: list[dict[str, str]],
) -> list[dict[str, str]]:
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for art in articles:
        key = art.get("title", "") or art.get("text", "")
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        out.append(art)
    return out


# ── fetching ──────────────────────────────────────────────────────────


def _fetch_team_articles(
    team: str,
    fetcher: Callable[[str], list[dict[str, str]]],
) -> list[dict[str, str]]:
    articles: list[dict[str, str]] = []
    # Search for multiple facets
    queries = [
        f"{team} football news",
        f"{team} World Cup news",
        f"{team} injury news",
        f"{team} recent form",
    ]
    for q in queries:
        try:
            batch = fetcher(q)
            articles.extend(batch)
        except Exception:
            continue
    return articles


def _build_default_fetcher(
    timeout: float,
) -> Callable[[str], list[dict[str, str]]]:
    def _fetcher(query: str) -> list[dict[str, str]]:
        return fetch_web_news(query, timeout=timeout)
    return _fetcher


def _duckduckgo_search(
    query: str,
    *,
    timeout: float = 10.0,
    source: str = "web",
) -> list[dict[str, str]]:
    """Search DuckDuckGo for news articles (uses ddgs or duckduckgo_search library)."""
    # Try the newer ddgs package first
    ddgs_mod = None
    try:
        import ddgs
        ddgs_mod = ddgs
    except ImportError:
        try:
            import duckduckgo_search as ddgs_mod  # noqa: F811
        except ImportError:
            return _duckduckgo_fallback(query, timeout=timeout, source=source)

    articles: list[dict[str, str]] = []
    try:
        results = ddgs_mod.DDGS(timeout=timeout).text(
            query, max_results=15, region="wt-wt"
        )
        for result in results:
            title = result.get("title", "")
            body = result.get("body", "")
            if title or body:
                articles.append({
                    "title": title.strip(),
                    "text": body.strip(),
                    "source": source,
                })
    except Exception:
        pass
    return articles


def _duckduckgo_fallback(
    query: str,
    *,
    timeout: float = 10.0,
    source: str = "web",
) -> list[dict[str, str]]:
    """HTML-scrape DuckDuckGo Lite as a fallback."""
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    url = f"https://html.duckduckgo.com/html/?{urlencode({'q': query})}"
    req = Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except (URLError, OSError):
        return []

    articles: list[dict[str, str]] = []
    snippet_re = re.compile(
        r'<a[^>]*class="result__a"[^>]*>(.*?)</a>.*?'
        r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
        re.DOTALL,
    )
    for match in snippet_re.finditer(raw):
        title = _strip_html(match.group(1))
        snippet = _strip_html(match.group(2))
        if title or snippet:
            articles.append({
                "title": title.strip(),
                "text": snippet.strip(),
                "source": source,
            })
    return articles


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&#x27;", "'")
