"""Tests for web search dedupe."""

from civilai_agent.guardrails.web_search_models import WebSearchConfig
from civilai_agent.tools.web_search import SearchSession, domain_allowed


def test_domain_allowed_requires_hostname_boundary() -> None:
    config = WebSearchConfig(
        allowed_domains=("texas.gov",),
        blocked_domains=("social.example",),
    )

    assert domain_allowed("https://tceq.texas.gov/gis", config) is True
    assert domain_allowed("https://texas.gov/", config) is True
    assert domain_allowed("https://nottexas.gov/", config) is False
    assert domain_allowed("https://texas.gov.evil.example/", config) is False
    assert domain_allowed("https://social.example/", config) is False


def test_domain_allowed_rejects_open_wildcard() -> None:
    config = WebSearchConfig(allowed_domains=("*.*",))

    assert domain_allowed("https://untrusted.example/", config) is False


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
        # Dedupe skips the provider but still returns the prior hits so the
        # model / debug trace do not see an empty search after prefetch.
        assert second == first
        assert session.dedupe_hits == 1
        assert _FakeProvider.calls == 1
        trace = session.get_trace()
        assert len(trace) == 2
        assert trace[0].dedupe_hit is False
        assert trace[1].dedupe_hit is True
        assert len(trace[1].results) == 1
    finally:
        ws.get_web_search_provider = original
