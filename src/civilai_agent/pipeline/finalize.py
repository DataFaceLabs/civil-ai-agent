"""Pipeline-only post-processing: disclaimer injection and guardrail refresh."""

from __future__ import annotations

from civilai_agent.guardrails.shared import DEFAULT_GUARDRAILS, evaluate_structured_guardrails
from civilai_agent.guardrails.structured import SectionDraftOutput
from civilai_agent.models.context import AgentResponse


def inject_utilities_disclaimer(response: AgentResponse) -> AgentResponse:
    """Append the required utilities disclaimer when absent (pipeline path only)."""
    if response.structured_draft is None:
        return response
    section_id = None
    if response.artifacts:
        section_id = response.artifacts[0].section_id
    if section_id != "utilities":
        return response

    structured = SectionDraftOutput.model_validate(response.structured_draft)
    disclaimer = DEFAULT_GUARDRAILS.required_disclaimers[0]
    blob = "\n".join([structured.suggested_language, *structured.caveats]).lower()
    if disclaimer.lower() in blob:
        return response

    updated = structured.model_copy(update={"caveats": (*structured.caveats, disclaimer)})
    warnings = evaluate_structured_guardrails(
        updated, DEFAULT_GUARDRAILS, section_id="utilities"
    )
    artifact = response.artifacts[0] if response.artifacts else None
    new_artifacts = response.artifacts
    if artifact is not None:
        new_meta = dict(artifact.metadata)
        new_meta["caveats"] = list(updated.caveats)
        new_artifacts = (
            artifact.model_copy(
                update={
                    "body": updated.suggested_language,
                    "claims": artifact.claims,
                    "data_gaps": updated.data_gaps,
                    "metadata": new_meta,
                }
            ),
        )
    return response.model_copy(
        update={
            "structured_draft": updated.model_dump(),
            "guardrail_warnings": warnings,
            "artifacts": new_artifacts,
        }
    )


def finalize_pipeline_response(response: AgentResponse) -> AgentResponse:
    """Apply pipeline-only finalization steps before returning to the harness."""
    return inject_utilities_disclaimer(response)
