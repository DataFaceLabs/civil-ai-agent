"""Unknown-fact rewrite on drafted study prose."""

from __future__ import annotations

import json

from civilai_agent.guardrails.finalize import finalize_text_output
from civilai_agent.guardrails.unknown_fact import rewrite_unknown_fact_prose

_CWQZ = (
    "Critical Water Quality Zone designation are not provided in the available "
    "field data and should be confirmed"
)
_CWQZ_EXPECTED = (
    "Critical Water Quality Zone designation not currently known and should be confirmed"
)


def test_rewrite_unknown_fact_prose_cwqz_example() -> None:
    assert rewrite_unknown_fact_prose(_CWQZ) == _CWQZ_EXPECTED
    assert (
        rewrite_unknown_fact_prose(
            "Setbacks are not in the available field data and should be confirmed."
        )
        == "Setbacks not currently known and should be confirmed."
    )
    assert (
        rewrite_unknown_fact_prose("Flood zone is not present in the field data.")
        == "Flood zone not currently known."
    )
    assert (
        rewrite_unknown_fact_prose("Overlay is not available from current project data.")
        == "Overlay is not currently known."
    )


def test_finalize_rewrites_structured_suggested_language() -> None:
    payload = json.dumps(
        {
            "suggested_language": _CWQZ,
            "caveats": [],
            "verification_steps": [],
            "data_gaps": [],
            "sources": [],
        }
    )
    display, structured, warnings = finalize_text_output(
        text=payload,
        structured_mode=True,
        section_id="environmental",
    )
    assert warnings == ()
    assert display == _CWQZ_EXPECTED
    assert structured is not None
    assert structured.suggested_language == _CWQZ_EXPECTED
    assert "available field data" not in structured.suggested_language


def test_finalize_rewrites_plain_chat_text() -> None:
    display, structured, _warnings = finalize_text_output(
        text=_CWQZ,
        structured_mode=False,
        section_id="environmental",
    )
    assert structured is None
    assert display == _CWQZ_EXPECTED
    assert "available field data" not in display.lower()
