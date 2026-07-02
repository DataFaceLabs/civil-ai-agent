"""Web search tool with session dedupe and provider cache."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Literal, Protocol
from urllib.parse import urlparse

import httpx

from civilai_agent.guardrails.web_search_models import WebSearchConfig, WebSearchResult
from civilai_agent.guardrails.web_search_query import normalize_search_query, simplify_search_query

logger = logging.getLogger(__name__)

_CACHE_TTL_SEC = 300.0
_search_cache: dict[str, tuple[float, tuple[WebSearchResult, ...]]] = {}

WebSearchProviderName = Literal["tavily", "serper", "brave"]


class WebSearchProvider(Protocol):
    def search(
        self,
        query: str,
        config: WebSearchConfig,
        *,
        restrict_domains: bool = False,
    ) -> tuple[WebSearchResult, ...]: ...


class TavilyWebSearchProvider:
    def search(
        self,
        query: str,
        config: WebSearchConfig,
        *,
        restrict_domains: bool = False,
    ) -> tuple[WebSearchResult, ...]:
        api_key = os.getenv("CIVILAI_TAVILY_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("CIVILAI_TAVILY_API_KEY is not set.")
        payload: dict[str, object] = {
            "api_key": api_key,
            "query": query,
            "max_results": config.max_results_per_query,
            "search_depth": config.search_depth,
        }
        if restrict_domains and config.allowed_domains:
            payload["include_domains"] = list(config.allowed_domains)
        timeout = float(os.getenv("CIVILAI_WEB_SEARCH_TIMEOUT_SEC", "15"))
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
    name = os.getenv("CIVILAI_WEB_SEARCH_PROVIDER", "tavily").strip().lower()
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
            return ()

        cache_key = _cache_key(normalize_search_query(query), self.config)
        cached = _from_cache(cache_key)
        if cached is not None:
            self._seen.add(key)
            self.dedupe_hits += 1
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
                results = provider.search(simplified, self.config, restrict_domains=restrict_domains)

        self._seen.add(key)
        self.executed_queries += 1
        _search_cache[cache_key] = (time.monotonic(), results)
        return results


def domain_allowed(url: str, config: WebSearchConfig) -> bool:
    host = urlparse(url).netloc.lower()
    if config.blocked_domains and any(host.endswith(d.lower()) for d in config.blocked_domains):
        return False
    if config.allowed_domains:
        return any(host.endswith(d.lower()) for d in config.allowed_domains)
    return True
