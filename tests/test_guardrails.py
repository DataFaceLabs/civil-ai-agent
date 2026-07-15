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


def test_will_serve_negative_capacity_sentence_not_flagged() -> None:
    # The exact cautionary form real drafts emit: coverage != capacity, listing
    # "will-serve commitment" among things NOT confirmed. Must not be flagged.
    output = SectionDraftOutput(
        suggested_language=(
            "These service-area findings indicate boundary coverage only and do not "
            "confirm available capacity, tap availability, pressure, fire-flow, or "
            "will-serve commitment."
        )
    )
    warnings = evaluate_structured_guardrails(output, DEFAULT_GUARDRAILS, section_id="utilities")
    assert not any("forbidden phrase: 'will-serve'" in w for w in warnings)


def test_will_serve_affirmative_claim_still_flagged() -> None:
    # Actually overclaiming capacity -- this must still be caught.
    output = SectionDraftOutput(suggested_language="The provider will-serve the site.")
    warnings = evaluate_structured_guardrails(output, DEFAULT_GUARDRAILS, section_id="utilities")
    assert any("forbidden phrase: 'will-serve'" in w for w in warnings)


def test_will_serve_affirmative_commitment_now_flagged() -> None:
    # Tightening: an affirmative issuance ("issued a will-serve commitment") is an
    # overclaim. The old noun-based safe markers let this slip; it must be caught now.
    output = SectionDraftOutput(
        suggested_language="The utility issued a will-serve commitment for the property."
    )
    warnings = evaluate_structured_guardrails(output, DEFAULT_GUARDRAILS, section_id="utilities")
    assert any("forbidden phrase: 'will-serve'" in w for w in warnings)


def test_guaranteed_capacity_contextual() -> None:
    # Affirmative claim is flagged; negated/cautionary form is not.
    flagged = evaluate_structured_guardrails(
        SectionDraftOutput(suggested_language="The site has guaranteed capacity for 200 LUEs."),
        DEFAULT_GUARDRAILS,
        section_id="utilities",
    )
    assert any("forbidden phrase: 'guaranteed capacity'" in w for w in flagged)

    safe = evaluate_structured_guardrails(
        SectionDraftOutput(
            suggested_language="Coverage does not indicate guaranteed capacity for the parcel."
        ),
        DEFAULT_GUARDRAILS,
        section_id="utilities",
    )
    assert not any("forbidden phrase: 'guaranteed capacity'" in w for w in safe)


def test_confirmed_service_commitment_contextual() -> None:
    flagged = evaluate_structured_guardrails(
        SectionDraftOutput(
            suggested_language="There is a confirmed service commitment from the city."
        ),
        DEFAULT_GUARDRAILS,
        section_id="utilities",
    )
    assert any("forbidden phrase: 'confirmed service commitment'" in w for w in flagged)

    safe = evaluate_structured_guardrails(
        SectionDraftOutput(
            suggested_language="There is no confirmed service commitment on record."
        ),
        DEFAULT_GUARDRAILS,
        section_id="utilities",
    )
    assert not any("forbidden phrase: 'confirmed service commitment'" in w for w in safe)


def test_disclaimer_satisfied_by_exact_text() -> None:
    # Backward compat: the literal sentence still satisfies the check.
    warnings = evaluate_guardrails(
        "Utility service boundaries indicate coverage only; capacity and will-serve are "
        "not confirmed. Water is provided by the City of Austin.",
        DEFAULT_GUARDRAILS,
        section_id="utilities",
    )
    assert not any("missing required disclaimer" in w for w in warnings)


def test_disclaimer_satisfied_by_paraphrase() -> None:
    # Regression test: real Haiku-generated drafts never emit the literal canned
    # sentence (verified 22/22 utilities drafts on disk, 100% false positive under the
    # old exact-match check) but do correctly convey the concept in their own words.
    # These two sentences are drawn verbatim from real agent output.
    for sentence in (
        "Coverage within a CCN service territory indicates the provider's jurisdiction "
        "only and does not confirm capacity or will-serve availability.",
        "However, service-territory coverage is not equivalent to confirmed capacity "
        "or will-serve.",
        "However, coverage does not guarantee capacity or a will-serve commitment.",
    ):
        warnings = evaluate_guardrails(sentence, DEFAULT_GUARDRAILS, section_id="utilities")
        assert not any("missing required disclaimer" in w for w in warnings), (
            f"should have been satisfied by: {sentence!r}"
        )


def test_disclaimer_still_flagged_when_concept_absent() -> None:
    # A draft that discusses coverage but never actually distinguishes it from
    # capacity/will-serve must still be flagged -- the fix is not a neutered no-op.
    warnings = evaluate_guardrails(
        "The property is within Austin Water's CCN coverage area and Austin Energy's "
        "service territory. Fire protection is provided by the Austin Fire Department.",
        DEFAULT_GUARDRAILS,
        section_id="utilities",
    )
    assert any("missing required disclaimer" in w for w in warnings)


def test_disclaimer_semantic_check_only_applies_to_coverage_capacity_wording() -> None:
    # A differently-worded disclaimer that isn't about coverage/capacity falls back to
    # exact match rather than silently degrading to a permissive concept check.
    config = GuardrailConfig(
        required_disclaimers=("Consult a licensed surveyor before construction.",),
        disclaimer_sections=frozenset({"utilities"}),
    )
    warnings = evaluate_guardrails(
        "Coverage does not confirm capacity or will-serve.", config, section_id="utilities"
    )
    assert any("missing required disclaimer" in w for w in warnings)


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
