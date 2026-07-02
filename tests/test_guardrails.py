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
