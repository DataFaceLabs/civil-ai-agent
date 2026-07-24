"""Web search tool with session dedupe and provider cache."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Literal, Protocol
from urllib.parse import urlparse

import httpx

from civilai_agent.config import settings
from civilai_agent.guardrails.web_search_models import (
    WebSearchConfig,
    WebSearchResult,
    WebSearchTraceEntry,
)
from civilai_agent.guardrails.web_search_query import normalize_search_query, simplify_search_query

logger = logging.getLogger(__name__)

_CACHE_TTL_SEC = 300.0
_search_cache: dict[str, tuple[float, tuple[WebSearchResult, ...]]] = {}

WebSearchProviderName = Literal["tavily", "serper", "brave"]


class WebSearchProvider(Protocol):
    """Interface a search backend must satisfy (Tavily today; others pluggable)."""

    def search(
        self,
        query: str,
        config: WebSearchConfig,
        *,
        restrict_domains: bool = False,
    ) -> tuple[WebSearchResult, ...]: ...


class TavilyWebSearchProvider:
    """Tavily-backed implementation of :class:`WebSearchProvider`."""

    def search(
        self,
        query: str,
        config: WebSearchConfig,
        *,
        restrict_domains: bool = False,
    ) -> tuple[WebSearchResult, ...]:
        api_key = settings().tavily_api_key.strip()
        if not api_key:
            logger.warning("CIVILAI_TAVILY_API_KEY is not set; skipping web search.")
            return ()
        payload: dict[str, object] = {
            "api_key": api_key,
            "query": query,
            "max_results": config.max_results_per_query,
            "search_depth": config.search_depth,
        }
        if restrict_domains and config.allowed_domains:
            payload["include_domains"] = list(config.allowed_domains)
        timeout = settings().web_search_timeout_sec
        with httpx.Client(timeout=timeout) as client:
            resp = client.post("https://api.tavily.com/search", json=payload)
            resp.raise_for_status()
            data = resp.json()
        results: list[WebSearchResult] = []
        for hit in data.get("results", []):
            if not isinstance(hit, dict):
                continue
            url = str(hit.get("url", "")).strip()
            if not url:
                continue
            results.append(
                WebSearchResult(
                    title=str(hit.get("title", "")).strip() or url,
                    url=url,
                    snippet=str(hit.get("content", "")).strip()[:500],
                )
            )
        return tuple(results)


def get_web_search_provider() -> WebSearchProvider:
    """Instantiate the configured provider (only Tavily is implemented)."""
    name = settings().web_search_provider.strip().lower()
    if name != "tavily":
        raise RuntimeError(f"Unsupported web search provider: {name}")
    return TavilyWebSearchProvider()


def _cache_key(query: str, config: WebSearchConfig) -> str:
    payload = {"q": query, "depth": config.search_depth, "max": config.max_results_per_query}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _from_cache(key: str) -> tuple[WebSearchResult, ...] | None:
    entry = _search_cache.get(key)
    if entry is None:
        return None
    ts, results = entry
    if time.monotonic() - ts > _CACHE_TTL_SEC:
        _search_cache.pop(key, None)
        return None
    return results


class SearchSession:
    """Tracks executed queries to prevent duplicate provider calls."""

    def __init__(self, config: WebSearchConfig | None = None) -> None:
        self.config = config or WebSearchConfig()
        self._seen: set[str] = set()
        self.dedupe_hits = 0
        self.executed_queries = 0
        self._trace_entries: list[WebSearchTraceEntry] = []

    def get_trace(self) -> tuple[WebSearchTraceEntry, ...]:
        return tuple(self._trace_entries)

    def _normalize_key(self, query: str, entity_id: str | None = None) -> str:
        base = normalize_search_query(query).lower()
        if entity_id:
            return f"{entity_id}:{base}"
        return base

    def search(
        self,
        query: str,
        *,
        entity_id: str | None = None,
        restrict_domains: bool = False,
    ) -> tuple[WebSearchResult, ...]:
        key = self._normalize_key(query, entity_id)
        if key in self._seen:
            self.dedupe_hits += 1
            logger.info("web_search dedupe hit: %s", query)
            self._trace_entries.append(
                WebSearchTraceEntry(query=query, results=(), dedupe_hit=True)
            )
            return ()

        cache_key = _cache_key(normalize_search_query(query), self.config)
        cached = _from_cache(cache_key)
        if cached is not None:
            self._seen.add(key)
            self.dedupe_hits += 1
            self._trace_entries.append(
                WebSearchTraceEntry(query=query, results=cached, dedupe_hit=True)
            )
            return cached

        provider = get_web_search_provider()
        results = provider.search(
            normalize_search_query(query),
            self.config,
            restrict_domains=restrict_domains,
        )
        if not results:
            simplified = simplify_search_query(query)
            if simplified != normalize_search_query(query):
                results = provider.search(
                    simplified, self.config, restrict_domains=restrict_domains
                )

        self._seen.add(key)
        self.executed_queries += 1
        _search_cache[cache_key] = (time.monotonic(), results)
        self._trace_entries.append(
            WebSearchTraceEntry(query=query, results=results, dedupe_hit=False)
        )
        return results


def _domain_matches(host: str, configured_domain: str) -> bool:
    domain = configured_domain.strip().lower().lstrip(".")
    if domain.startswith("*."):
        domain = domain[2:]
    if not domain or domain in {"*", "*.*"}:
        return False
    return host == domain or host.endswith(f".{domain}")


def domain_allowed(url: str, config: WebSearchConfig) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if config.blocked_domains and any(
        _domain_matches(host, domain) for domain in config.blocked_domains
    ):
        return False
    if config.allowed_domains:
        return any(_domain_matches(host, domain) for domain in config.allowed_domains)
    return True
