"""Tests for pipeline-only finalization."""

from __future__ import annotations

from civilai_agent.guardrails.shared import DEFAULT_GUARDRAILS
from civilai_agent.guardrails.structured import SectionDraftOutput
from civilai_agent.models.context import AgentArtifact, AgentResponse, Claim
from civilai_agent.pipeline.finalize import (
    append_fact_echo_warnings,
    finalize_pipeline_response,
    inject_utilities_disclaimer,
)


def _utilities_response(*, with_disclaimer: bool) -> AgentResponse:
    caveats: tuple[str, ...] = ()
    if with_disclaimer:
        caveats = (DEFAULT_GUARDRAILS.required_disclaimers[0],)
    structured = SectionDraftOutput(
        suggested_language="Water and wastewater service areas are mapped for this parcel.",
        caveats=caveats,
    )
    artifact = AgentArtifact(
        type="draft_section",
        title="Draft — utilities",
        status="partial",
        section_id="utilities",
        claims=(Claim(text=structured.suggested_language),),
        body=structured.suggested_language,
    )
    warnings: tuple[str, ...] = ()
    if not with_disclaimer:
        warnings = ("Output missing required disclaimer: ...",)
    return AgentResponse(
        message=structured.suggested_language,
        artifacts=(artifact,),
        structured_draft=structured.model_dump(),
        guardrail_warnings=warnings,
    )


def test_inject_utilities_disclaimer_appends_when_missing() -> None:
    response = _utilities_response(with_disclaimer=False)
    updated = inject_utilities_disclaimer(response)
    assert updated.structured_draft is not None
    caveats = updated.structured_draft["caveats"]
    assert DEFAULT_GUARDRAILS.required_disclaimers[0] in caveats
    assert not any("missing required disclaimer" in w for w in updated.guardrail_warnings)


def test_inject_utilities_disclaimer_noop_when_present() -> None:
    response = _utilities_response(with_disclaimer=True)
    updated = inject_utilities_disclaimer(response)
    assert updated == response


def test_append_fact_echo_warnings_merges_into_response() -> None:
    from civilai_agent.pipeline.specs import DraftSpec

    structured = SectionDraftOutput(
        suggested_language="This property is not subject to zoning regulations."
    )
    artifact = AgentArtifact(
        type="draft_section",
        title="Draft — zoning",
        status="partial",
        section_id="zoning",
        claims=(Claim(text=structured.suggested_language),),
        body=structured.suggested_language,
    )
    response = AgentResponse(
        message=structured.suggested_language,
        artifacts=(artifact,),
        structured_draft=structured.model_dump(),
    )
    spec = DraftSpec(
        entity_id="ent-1",
        section_id="zoning",
        branch_id="zoning.zoned_city",
        tier=2,
        slots={"zoning_code": "DR"},
    )
    updated = append_fact_echo_warnings(response, spec)
    assert len(updated.guardrail_warnings) == 1
    assert "zoning_code" in updated.guardrail_warnings[0]


def test_finalize_pipeline_response_non_utilities_unchanged() -> None:
    structured = SectionDraftOutput(suggested_language="Zoning is CS.")
    artifact = AgentArtifact(
        type="draft_section",
        title="Draft — zoning",
        status="partial",
        section_id="zoning",
        claims=(Claim(text=structured.suggested_language),),
        body=structured.suggested_language,
    )
    response = AgentResponse(
        message=structured.suggested_language,
        artifacts=(artifact,),
        structured_draft=structured.model_dump(),
    )
    assert finalize_pipeline_response(response) == response
