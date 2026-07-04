"""Tests for parse_structured_response's JSON extraction.

test_prose_preamble_then_fenced_json reproduces a real live failure: running the
eval harness (docs/agent-tuning-strategy.md's Phase 2 tooling) against parcel 102902 on
Haiku 4.5, the model prefixed its structured response with a conversational sentence and
wrapped the JSON in a ```json fence anyway, despite the prompt explicitly asking for a
bare object with no fence (workflows/section_draft.py's STRUCTURED_DRAFT_INSTRUCTION).
The old anchored-fence regex required the *entire* trimmed text to be the fence, so it
never matched, and json.loads then failed on the leading prose with "Expecting value:
line 1 column 1" -- artifacts stayed empty in production even after Phase 1 (PR #10)
supposedly fixed exactly that.
"""

from __future__ import annotations

from civilai_agent.guardrails.structured import parse_structured_response

_MINIMAL = {
    "suggested_language": "The subject property is zoned MF-2.",
    "caveats": [],
    "verification_steps": [],
    "data_gaps": [],
    "sources": [],
}


def test_bare_json_no_fence() -> None:
    text = (
        '{"suggested_language": "The subject property is zoned MF-2.", '
        '"caveats": [], "verification_steps": [], "data_gaps": [], "sources": []}'
    )
    result, errors = parse_structured_response(text)
    assert result is not None
    assert errors == ()
    assert result.suggested_language == "The subject property is zoned MF-2."


def test_whole_response_is_a_fenced_block() -> None:
    text = (
        "```json\n"
        '{"suggested_language": "The subject property is zoned MF-2.", '
        '"caveats": [], "verification_steps": [], "data_gaps": [], "sources": []}\n'
        "```"
    )
    result, _ = parse_structured_response(text)
    assert result is not None
    assert result.suggested_language == "The subject property is zoned MF-2."


def test_prose_preamble_then_fenced_json() -> None:
    """The exact live failure mode: prose sentence, then a fenced JSON block."""
    text = (
        "Based on the governed data retrieved, I can now draft the Zoning section. "
        "The property is within City of Austin full-purpose jurisdiction, zoned MF-2 "
        "(Multi-Family Limited Density), with no overlays, and the proposed use is not "
        "specified. I'll draft the section following the ATX-Civil pattern.\n\n"
        "```json\n"
        '{"suggested_language": "The subject property is zoned MF-2.", '
        '"caveats": [], "verification_steps": [], "data_gaps": [], "sources": []}\n'
        "```"
    )
    result, errors = parse_structured_response(text)
    assert result is not None, f"expected a parse, got errors: {errors}"
    assert result.suggested_language == "The subject property is zoned MF-2."


def test_prose_preamble_then_unfenced_json() -> None:
    text = (
        "Here is the drafted section:\n"
        '{"suggested_language": "The subject property is zoned MF-2.", '
        '"caveats": [], "verification_steps": [], "data_gaps": [], "sources": []}'
    )
    result, _ = parse_structured_response(text)
    assert result is not None
    assert result.suggested_language == "The subject property is zoned MF-2."


def test_unparseable_text_returns_none_with_errors() -> None:
    result, errors = parse_structured_response("I could not draft this section.")
    assert result is None
    assert errors
    assert all("JSON parse error" in e for e in errors)


def test_valid_json_failing_schema_reports_validation_errors() -> None:
    result, errors = parse_structured_response('{"unexpected_field": "x"}')
    assert result is None
    assert errors
    assert not any("JSON parse error" in e for e in errors)
