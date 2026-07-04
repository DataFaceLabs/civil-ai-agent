"""Tests for guardrails and structured output."""

from civilai_agent.guardrails.finalize import finalize_text_output
from civilai_agent.guardrails.shared import GuardrailConfig


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
