"""Tests for pipeline-only finalization."""

from __future__ import annotations

from civilai_agent.guardrails.shared import DEFAULT_GUARDRAILS
from civilai_agent.guardrails.structured import SectionDraftOutput
from civilai_agent.models.context import AgentArtifact, AgentResponse, Claim
from civilai_agent.pipeline.finalize import finalize_pipeline_response, inject_utilities_disclaimer


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
