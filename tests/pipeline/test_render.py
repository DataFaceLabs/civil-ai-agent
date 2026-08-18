"""Tests for pipeline renderer (S2.1)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from civilai_agent.pipeline.render import (
    RENDERER_SYSTEM_PROMPT,
    build_render_prompt,
    build_renderer_agent,
    render_draft,
)
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


def test_renderer_system_prompt_requires_gis_viewer_markdown_hrefs() -> None:
    assert "apps/mapviewer" in RENDERER_SYSTEM_PROMPT
    assert "[source_name](url)" in RENDERER_SYSTEM_PROMPT


def test_build_render_prompt_ships_only_field_values_not_raw_payload() -> None:
    """Cost fix (2026-07-16): the render prompt must send only the governed field values,
    not the full section-facts payload. The raw `evidence` block (per-field source arrays)
    is the single largest chunk and is already distilled into `citations`, so shipping it
    re-sends the same sources twice. `provenance`/`quality`/`as_of` are never read by the
    renderer. Trimming these cut real UAT render prompts ~60% with no output change."""
    spec = _sample_spec()
    # Simulate the real data-API shape: field values wrapped under "facts", plus the
    # heavy metadata blocks the renderer never consumes.
    spec.facts = {
        "entity_id": "ent-bullick",
        "section_id": "zoning",
        "as_of": "2026-07-15",
        "facts": {"zoning_code": "DR", "jurisdiction_primary": "City of Austin limited purpose"},
        "evidence": {
            "zoning_code": [
                {"citation_url": "https://evidence.example/zoning", "source_name": "COA GIS"}
            ]
        },
        "provenance": {"pipeline": "phase1", "run_id": "SHOULD_NOT_APPEAR"},
        "quality": {"zoning_code": "confirmed"},
    }
    prompt = build_render_prompt(spec)
    # Field values survive.
    assert "zoning_code" in prompt
    assert "DR" in prompt
    # Heavy, renderer-irrelevant payload is gone.
    assert "https://evidence.example/zoning" not in prompt
    assert "SHOULD_NOT_APPEAR" not in prompt
    assert '"quality"' not in prompt
    assert '"as_of"' not in prompt


def test_build_render_prompt_uses_compact_json() -> None:
    """Compact separators (no indent) materially reduce input tokens; guard against a
    regression back to indent=2 pretty-printing of the governed field values."""
    spec = _sample_spec()
    spec.facts = {"facts": {"zoning_code": "DR", "jurisdiction_primary": "COA"}}
    prompt = build_render_prompt(spec)
    # Compact form has no space after the colon or comma...
    assert '"zoning_code":"DR"' in prompt
    # ...and never the indent=2 pretty-printed form.
    assert '"zoning_code": "DR"' not in prompt


def test_build_render_prompt_omits_format_section_when_directive_empty() -> None:
    prompt = build_render_prompt(_sample_spec())
    assert "Section formatting requirements" not in prompt


def test_build_render_prompt_includes_format_directive_when_provided() -> None:
    """UAT (2026-07-15): pipeline-rendered sections (zoning, environmental, ...) came back
    as flat unheaded prose because the renderer never saw the tenant's Prompt Lab subsection/
    heading instructions -- only the legacy agent path did. This asserts the fix: the tenant's
    format directive reaches the prompt, clearly scoped to structure, not facts."""
    directive = (
        "Produce the following subsections, in order:\n\nEcoregion — ...\n\n"
        "Format: subsections with the headings above."
    )
    prompt = build_render_prompt(_sample_spec(), format_directive=directive)
    assert "Section formatting requirements" in prompt
    assert directive in prompt
    assert "do not source facts from this" in prompt


@patch("civilai_agent.pipeline.render.build_renderer_agent")
def test_render_draft_threads_format_directive_into_prompt(mock_build: MagicMock) -> None:
    agent = MagicMock()
    agent.return_value = _structured_json()
    mock_build.return_value = agent

    render_draft(_sample_spec(), format_directive="Format: use headings above.")

    prompt = agent.call_args[0][0]
    assert "Section formatting requirements" in prompt
    assert "Format: use headings above." in prompt


def test_build_renderer_agent_appends_tenant_system_prompt() -> None:
    """UAT (2026-07-15): James's finding, confirmed -- the tenant's *system* prompt
    (context.system_prompt) carries the master 'Format: h1 and h2 subsections with
    headings... Emit field data facts in bold' mandate. This is what makes legacy-path
    sections (Parcel, Access) render with real markdown structure, and it's the piece the
    pipeline renderer dropped entirely (it always used its own hardcoded system prompt).
    Asserts the tenant's mandate now reaches the agent's actual system prompt, additively."""
    agent = build_renderer_agent(
        tenant_system_prompt="Format: h1 and h2 subsections with headings. Emit facts in bold."
    )
    system_prompt = agent.system_prompt
    assert "Format: h1 and h2 subsections with headings." in system_prompt
    assert "known site facts, branches, and tools still control content" in system_prompt
    # The pipeline's own mechanical rules (don't re-decide, don't contradict facts) survive.
    assert "re-decide feasibility" in system_prompt


def test_build_renderer_agent_omits_tenant_block_when_empty() -> None:
    agent = build_renderer_agent()
    assert agent.system_prompt == RENDERER_SYSTEM_PROMPT


@patch("civilai_agent.pipeline.render.build_renderer_agent")
def test_render_draft_threads_tenant_system_prompt(mock_build: MagicMock) -> None:
    agent = MagicMock()
    agent.return_value = _structured_json()
    mock_build.return_value = agent

    render_draft(_sample_spec(), tenant_system_prompt="Format: h1 and h2 headings.")

    mock_build.assert_called_once_with(
        model_id=None, tenant_system_prompt="Format: h1 and h2 headings."
    )


@patch("civilai_agent.pipeline.render.build_renderer_agent")
def test_render_draft_parses_canned_response(mock_build: MagicMock) -> None:
    agent = MagicMock()
    agent.return_value = _structured_json()
    mock_build.return_value = agent

    result = render_draft(_sample_spec(), model_id="test-model")

    assert "DR" in result.output.suggested_language
    assert result.output.data_gaps == ("proposed_use not specified",)
    mock_build.assert_called_once_with(model_id="test-model", tenant_system_prompt="")
    agent.assert_called_once()
    prompt = agent.call_args[0][0]
    assert "zoning.coa_limited_purpose" in prompt


@patch("civilai_agent.pipeline.render.build_renderer_agent")
def test_render_draft_retries_once_then_raises(mock_build: MagicMock) -> None:
    agent = MagicMock()
    agent.return_value = "Plain prose without JSON."
    mock_build.return_value = agent

    with pytest.raises(RuntimeError, match="Renderer failed to produce structured output"):
        render_draft(_sample_spec())

    assert agent.call_count == 2
    retry_prompt = agent.call_args[0][0]
    assert "failed structured validation" in retry_prompt


@patch("civilai_agent.pipeline.render.build_renderer_agent")
def test_render_draft_recovers_on_retry(mock_build: MagicMock) -> None:
    agent = MagicMock()
    agent.side_effect = ["Plain prose without JSON.", _structured_json()]
    mock_build.return_value = agent

    result = render_draft(_sample_spec())

    assert agent.call_count == 2
    assert "DR" in result.output.suggested_language


@patch("civilai_agent.pipeline.render.build_renderer_agent")
def test_render_draft_records_token_usage(mock_build: MagicMock) -> None:
    """Telemetry: pipeline renders previously reported zero tokens (per-draft cost was
    invisible). RenderResult must surface the usage Strands returns."""
    raw = MagicMock()
    raw.message = _structured_json()
    raw.metrics.accumulated_usage = {"inputTokens": 1234, "outputTokens": 567}
    agent = MagicMock(return_value=raw)
    mock_build.return_value = agent

    result = render_draft(_sample_spec())

    assert result.input_tokens == 1234
    assert result.output_tokens == 567
