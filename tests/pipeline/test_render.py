"""Tests for pipeline renderer (S2.1)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from civilai_agent.pipeline.render import build_render_prompt, render_draft
from civilai_agent.pipeline.specs import DraftSpec, MissingInput


def _sample_spec() -> DraftSpec:
    return DraftSpec(
        entity_id="ent-bullick",
        section_id="zoning",
        branch_id="zoning.coa_limited_purpose",
        tier=2,
        slots={
            "zoning_code": "DR",
            "jurisdiction_primary": "City of Austin limited purpose",
        },
        facts={"zoning_code": "DR", "jurisdiction_primary": "City of Austin limited purpose"},
        determinations=[{"determination_id": "zoning_applies", "conclusion": "yes"}],
        citations=[{"source": "coa_zoning", "field": "zoning_code"}],
        stems=["State that DR zoning applies under limited-purpose jurisdiction."],
        missing_inputs=[
            MissingInput(
                name="proposed_use",
                why_needed="Rezoning verdict requires client's intended use.",
                resolution="client",
            )
        ],
    )


def _structured_json() -> str:
    return json.dumps(
        {
            "suggested_language": (
                "The parcel is within the City of Austin limited-purpose jurisdiction "
                "and is zoned DR (Development Reserve)."
            ),
            "caveats": [],
            "verification_steps": ["Confirm proposed use with the client."],
            "data_gaps": ["proposed_use not specified"],
            "sources": [],
        }
    )


def test_build_render_prompt_includes_spec_fields() -> None:
    prompt = build_render_prompt(_sample_spec())
    assert "zoning.coa_limited_purpose" in prompt
    assert "DR" in prompt
    assert "proposed_use" in prompt
    assert "Required prose stems" in prompt
    assert "suggested_language" in prompt


@patch("civilai_agent.pipeline.render.build_renderer_agent")
def test_render_draft_parses_canned_response(mock_build: MagicMock) -> None:
    agent = MagicMock()
    agent.return_value = _structured_json()
    mock_build.return_value = agent

    output = render_draft(_sample_spec(), model_id="test-model")

    assert "DR" in output.suggested_language
    assert output.data_gaps == ("proposed_use not specified",)
    mock_build.assert_called_once_with(model_id="test-model")
    agent.assert_called_once()
    prompt = agent.call_args[0][0]
    assert "zoning.coa_limited_purpose" in prompt


@patch("civilai_agent.pipeline.render.build_renderer_agent")
def test_render_draft_raises_on_parse_failure(mock_build: MagicMock) -> None:
    agent = MagicMock()
    agent.return_value = "Plain prose without JSON."
    mock_build.return_value = agent

    with pytest.raises(RuntimeError, match="Renderer failed to produce structured output"):
        render_draft(_sample_spec())
