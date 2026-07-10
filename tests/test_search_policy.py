"""Tests for SearchRunPolicy → WebSearchConfig mapping."""

from civilai_agent.guardrails.web_search_models import WebSearchConfig
from civilai_agent.models.search_policy import SearchRunPolicy


def test_from_search_run_policy_maps_fields() -> None:
    policy = SearchRunPolicy(
        enabled=True,
        search_context_hint="Austin zoning code",
        allowed_domains=("austintexas.gov",),
        blocked_domains=("reddit.com",),
        max_queries_per_run=2,
        query_mode="hybrid",
    )
    config = WebSearchConfig.from_search_run_policy(policy)
    assert config.enabled is True
    assert config.search_context_hint == "Austin zoning code"
    assert config.allowed_domains == ("austintexas.gov",)
    assert config.blocked_domains == ("reddit.com",)
    assert config.max_queries_per_invoke == 2
    assert config.query_mode == "hybrid"
    assert config.restrict_provider_domains is True
