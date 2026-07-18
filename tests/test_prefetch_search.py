"""Tests for guardrails/prefetch_search.py (X2 registry-drift regression).

The backend (civil-ai-data) field-code catalog has no ``ZONING_DISTRICT`` -- only
``ZONING_REGS`` exists. Referencing the wrong code meant ``field_context`` could
never populate it (the backend never emits a field under that name), so the
``elif zoning and juris`` branch in ``derive_prefetch_queries`` was permanently dead:
confirmed drift between this repo's hardcoded field list and the backend's actual
vocabulary (X2). Fixed by reading ``ZONING_REGS`` instead.
"""

from __future__ import annotations

from civilai_agent.guardrails.prefetch_search import (
    _PREFETCH_FIELD_CODES,
    derive_prefetch_queries,
)


def test_prefetch_field_codes_has_no_dead_zoning_district_reference() -> None:
    assert "ZONING_DISTRICT" not in _PREFETCH_FIELD_CODES
    assert "ZONING_REGS" in _PREFETCH_FIELD_CODES


def test_zoning_branch_fires_from_zoning_regs_not_impervious() -> None:
    """Regression: this branch was unreachable because it read a field code
    (ZONING_DISTRICT) the backend never populates. With ZONING_REGS supplied (and no
    IMPERVIOUS_REGS, which takes priority), the zoning query must now fire."""
    queries = derive_prefetch_queries(
        {
            "GOVERNING_JURIS": "City of Austin",
            "ZONING_REGS": "SF-3",
        }
    )
    assert any("zoning district" in q and "sf-3" in q.lower() for q in queries)


def test_impervious_takes_priority_over_zoning_when_both_present() -> None:
    queries = derive_prefetch_queries(
        {
            "GOVERNING_JURIS": "City of Austin",
            "ZONING_REGS": "SF-3",
            "IMPERVIOUS_REGS": "45%",
        }
    )
    assert any("impervious cover" in q for q in queries)
    assert not any("zoning district" in q for q in queries)


def test_no_queries_without_any_field_context() -> None:
    assert derive_prefetch_queries({}) == ()
