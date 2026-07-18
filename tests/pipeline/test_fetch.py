"""Tests for pipeline fetch layer."""

from __future__ import annotations

from typing import Any

from civilai_agent.pipeline.fetch import facts_nonempty, fetch_section_context
from civilai_agent.tools.data_client import DataApiClient, DataApiError


class FakeClient(DataApiClient):
    def __init__(self, **responses: Any) -> None:
        super().__init__(base_url="http://fake", timeout=1.0)
        self._responses = responses
        self.calls: list[tuple[str, str, str]] = []

    def get_section_facts(self, entity_id: str, section_id: str) -> dict[str, Any]:
        self.calls.append(("facts", entity_id, section_id))
        if "facts" in self._responses:
            val = self._responses["facts"]
            if isinstance(val, Exception):
                raise val
            return val
        raise DataApiError("facts unavailable", status_code=503)

    def run_determinations(self, entity_id: str) -> dict[str, Any]:
        self.calls.append(("determinations", entity_id, ""))
        if "determinations" in self._responses:
            val = self._responses["determinations"]
            if isinstance(val, Exception):
                raise val
            return val
        raise DataApiError("determinations unavailable", status_code=503)

    def get_provenance(self, entity_id: str) -> dict[str, Any]:
        self.calls.append(("provenance", entity_id, ""))
        if "provenance" in self._responses:
            val = self._responses["provenance"]
            if isinstance(val, Exception):
                raise val
            return val
        raise DataApiError("provenance unavailable", status_code=503)


def test_facts_nonempty_inner_dict() -> None:
    assert facts_nonempty({"facts": {"zoning_code": "CS"}})


def test_facts_nonempty_entity_id_only() -> None:
    assert facts_nonempty({"entity_id": "ent-1"})


def test_facts_nonempty_false_when_empty() -> None:
    assert not facts_nonempty({"facts": {}})
    assert not facts_nonempty(None)
    assert not facts_nonempty({})


def test_fetch_section_context_all_success() -> None:
    client = FakeClient(
        facts={"facts": {"zoning_code": "DR"}},
        determinations={"items": []},
        provenance={"sources": []},
    )
    ctx = fetch_section_context(client, "ent-abc", "zoning")
    assert ctx.entity_id == "ent-abc"
    assert ctx.section_id == "zoning"
    assert ctx.facts == {"facts": {"zoning_code": "DR"}}
    assert ctx.determinations == {"items": []}
    assert ctx.provenance == {"sources": []}
    assert ctx.errors == []
    assert len(client.calls) == 3


def test_fetch_section_context_captures_errors() -> None:
    client = FakeClient(
        facts=DataApiError("facts down", status_code=503),
        determinations={"items": []},
        provenance=DataApiError("provenance down", status_code=500),
    )
    ctx = fetch_section_context(client, "ent-xyz", "utilities")
    assert ctx.facts is None
    assert ctx.determinations == {"items": []}
    assert ctx.provenance is None
    assert len(ctx.errors) == 2
    assert "get_section_facts" in ctx.errors[0]
    assert "get_provenance" in ctx.errors[1]
