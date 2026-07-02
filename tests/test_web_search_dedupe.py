"""Tests for web search dedupe."""

from civilai_agent.guardrails.web_search_models import WebSearchConfig
from civilai_agent.tools.web_search import SearchSession


def test_search_session_dedupes_same_query() -> None:
    session = SearchSession(WebSearchConfig(enabled=True, max_queries_per_invoke=3))

    class _FakeProvider:
        calls = 0

        def search(self, query: str, config: WebSearchConfig, *, restrict_domains: bool = False):
            _FakeProvider.calls += 1
            from civilai_agent.guardrails.web_search_models import WebSearchResult

            return (WebSearchResult(title="t", url="https://example.com/a"),)

    import civilai_agent.tools.web_search as ws

    original = ws.get_web_search_provider
    ws.get_web_search_provider = lambda: _FakeProvider()  # type: ignore[assignment]
    try:
        first = session.search("Austin zoning code", entity_id="ent-1")
        second = session.search("Austin zoning code", entity_id="ent-1")
        assert len(first) == 1
        assert second == ()
        assert session.dedupe_hits == 1
        assert _FakeProvider.calls == 1
    finally:
        ws.get_web_search_provider = original
