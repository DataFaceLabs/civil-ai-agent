"""Normalize and expand deterministic web search queries."""

from __future__ import annotations

import re

_MAX_QUERY_LEN = 220

_WATERSHED_TAIL_RE = re.compile(
    r"\b(lake|town|creek|river|basin|watershed|huc\d+)\b",
    re.IGNORECASE,
)

_SEARCH_GUIDANCE_SUFFIX_RE = re.compile(
    r"\n\nSearch guidance:\s*.+",
    re.IGNORECASE | re.DOTALL,
)

_FIELD_TOKEN_RE = re.compile(r"\{\{field\.([A-Z0-9_]+)\}\}")

_HINT_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "for",
        "from",
        "in",
        "of",
        "official",
        "or",
        "prefer",
        "sources",
        "the",
        "to",
        "use",
    }
)


def normalize_search_query(query: str) -> str:
    collapsed = " ".join(query.split()).strip()
    if len(collapsed) <= _MAX_QUERY_LEN:
        return collapsed
    return collapsed[: _MAX_QUERY_LEN - 3].rstrip() + "..."


def simplify_search_query(query: str) -> str:
    words = query.split()
    if len(words) <= 6:
        return normalize_search_query(query)
    trimmed: list[str] = []
    for word in words:
        if _WATERSHED_TAIL_RE.search(word) and len(trimmed) >= 4:
            break
        trimmed.append(word)
    if len(trimmed) < 4:
        trimmed = words[:6]
    return normalize_search_query(" ".join(trimmed))


def strip_search_guidance_suffix(user_prompt: str) -> str:
    return _SEARCH_GUIDANCE_SUFFIX_RE.sub("", user_prompt).strip()


def resolve_field_tokens(text: str, field_context: dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        code = match.group(1)
        value = field_context.get(code, "").strip()
        return value if value else match.group(0)

    return _FIELD_TOKEN_RE.sub(repl, text)


def resolved_hint_has_unsubstituted_tokens(text: str) -> bool:
    return bool(_FIELD_TOKEN_RE.search(text))


def search_terms_from_context_hint(hint: str, *, max_words: int = 10) -> str:
    text = hint.strip()
    if not text:
        return ""
    for sep in (" for the ", ";"):
        idx = text.lower().find(sep)
        if idx >= 0:
            text = text[:idx].strip()
    tokens: list[str] = []
    for word in re.findall(r"[A-Za-z0-9]+", text):
        if word.lower() in _HINT_STOPWORDS:
            continue
        tokens.append(word)
        if len(tokens) >= max_words:
            break
    return " ".join(tokens)


def merge_query_with_hint(base: str, hint: str) -> str:
    terms = search_terms_from_context_hint(hint)
    if not terms:
        return normalize_search_query(base)
    return normalize_search_query(f"{base} {terms}")
