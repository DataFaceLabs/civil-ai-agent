"""Tests for guardrails and structured output."""

from civilai_agent.guardrails.finalize import finalize_text_output
from civilai_agent.guardrails.shared import (
    DEFAULT_GUARDRAILS,
    GuardrailConfig,
    evaluate_guardrails,
    evaluate_structured_guardrails,
)
from civilai_agent.guardrails.structured import SectionDraftOutput


def test_structured_guardrail_warns_on_forbidden_phrase() -> None:
    text = json_payload_with_will_serve()
    _, _, warnings = finalize_text_output(
        text=text,
        guardrails=GuardrailConfig(forbidden_phrases=("will-serve",)),
        structured_mode=True,
    )
    assert any("will-serve" in w for w in warnings)


def test_structured_parse_failure_warns_when_not_enforcing() -> None:
    _, structured, warnings = finalize_text_output(
        text="not json",
        guardrails=GuardrailConfig(enforce=False),
        structured_mode=True,
    )
    assert structured is None
    assert any("could not be parsed" in w.lower() for w in warnings)


def test_structured_parse_failure_raises_when_enforcing() -> None:
    import pytest

    with pytest.raises(RuntimeError, match="Structured agent response failed validation"):
        finalize_text_output(
            text="not json",
            guardrails=GuardrailConfig(enforce=True),
            structured_mode=True,
        )


def test_disclaimer_not_required_outside_configured_sections() -> None:
    # F3: the disclaimer is about utility coverage; a soils draft has no reason to
    # contain it, and blanket-checking it made every non-utility section fail.
    warnings = evaluate_guardrails(
        "The primary site soil is Heiden clay, HSG D.",
        DEFAULT_GUARDRAILS,
        section_id="soils",
    )
    assert not any("missing required disclaimer" in w for w in warnings)


def test_disclaimer_still_required_for_utilities_section() -> None:
    warnings = evaluate_guardrails(
        "Water is provided by the City of Austin.",
        DEFAULT_GUARDRAILS,
        section_id="utilities",
    )
    assert any("missing required disclaimer" in w for w in warnings)


def test_disclaimer_checked_when_section_unspecified() -> None:
    # Back-compat: callers that don't pass section_id keep the old blanket behavior.
    warnings = evaluate_guardrails("No disclaimer here.", DEFAULT_GUARDRAILS, section_id=None)
    assert any("missing required disclaimer" in w for w in warnings)


def test_will_serve_safe_recommendation_not_flagged() -> None:
    # Real, correct usage: recommending verification, not claiming capacity.
    output = SectionDraftOutput(
        suggested_language=(
            "Service-territory coverage does not confirm capacity or will-serve status; "
            "obtain a will-serve letter from the City of Austin Water Utility."
        )
    )
    warnings = evaluate_structured_guardrails(output, DEFAULT_GUARDRAILS, section_id="utilities")
    assert not any("forbidden phrase: 'will-serve'" in w for w in warnings)


def test_will_serve_affirmative_claim_still_flagged() -> None:
    # Actually overclaiming capacity -- this must still be caught.
    output = SectionDraftOutput(suggested_language="The provider will-serve the site.")
    warnings = evaluate_structured_guardrails(output, DEFAULT_GUARDRAILS, section_id="utilities")
    assert any("forbidden phrase: 'will-serve'" in w for w in warnings)


def json_payload_with_will_serve() -> str:
    return """
    {
      "suggested_language": "The provider will-serve wastewater.",
      "caveats": [],
      "verification_steps": [],
      "data_gaps": [],
      "sources": []
    }
    """
