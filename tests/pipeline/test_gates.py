"""Tests for pipeline zero-fact gate."""

from __future__ import annotations

from civilai_agent.pipeline.fetch import SectionContext
from civilai_agent.pipeline.gates import zero_fact_gate


def test_zero_fact_gate_returns_none_when_facts_present() -> None:
    ctx = SectionContext(
        entity_id="ent-1",
        section_id="zoning",
        facts={"facts": {"zoning_code": "CS"}},
    )
    assert zero_fact_gate(ctx) is None


def test_zero_fact_gate_returns_response_when_facts_missing() -> None:
    ctx = SectionContext(
        entity_id="ent-1801",
        section_id="zoning",
        facts=None,
        errors=["get_section_facts: GET /v1/... -> 404: not found"],
    )
    response = zero_fact_gate(ctx)
    assert response is not None
    assert "could not be drafted" in response.message
    assert response.artifacts
    artifact = response.artifacts[0]
    assert artifact.type == "draft_section"
    assert artifact.section_id == "zoning"
    assert artifact.data_gaps
    assert response.structured_draft is not None
    assert response.trace_summary is not None
    assert "pipeline_gate_zero_facts" in response.trace_summary.tools_used


def test_zero_fact_gate_section_title_in_message() -> None:
    ctx = SectionContext(entity_id="ent-1", section_id="utilities", facts={"facts": {}})
    response = zero_fact_gate(ctx)
    assert response is not None
    assert "Utilities section" in response.message
