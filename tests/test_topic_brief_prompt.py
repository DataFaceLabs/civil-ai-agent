"""Tests for Topic Hydrate prompt injection."""

from __future__ import annotations

from civilai_agent.models.context import WorkbenchContext
from civilai_agent.models.topic_brief import TopicBrief, TopicFieldExtract
from civilai_agent.pipeline.render import build_render_prompt
from civilai_agent.pipeline.specs import DraftSpec
from civilai_agent.pipeline.topic_brief_prompt import format_topic_briefs_block
from civilai_agent.workflows.section_draft import section_draft_prompt


def test_format_topic_briefs_block_includes_summary_and_fields() -> None:
    block = format_topic_briefs_block(
        [
            TopicBrief(
                topic_id="height_far",
                label="Height and FAR",
                status="complete",
                summary="Height comes from the map designation.",
                fields=(
                    TopicFieldExtract(
                        fe_code="GREEN_FACTOR_MIN",
                        value="0.5",
                        section_id="SEC1",
                        quote="minimum Green Factor score of 0.5",
                    ),
                ),
            )
        ]
    )
    assert "height_far" in block
    assert "GREEN_FACTOR_MIN" in block
    assert "do not re-search" in block


def test_build_render_prompt_includes_topic_briefs() -> None:
    spec = DraftSpec(
        entity_id="ent-1",
        section_id="zoning",
        branch_id="zoning_district",
        tier=1,
        topic_briefs=[
            TopicBrief(
                topic_id="height_far",
                label="Height and FAR",
                status="summary_only",
                summary="Summary-only topic.",
            )
        ],
    )
    prompt = build_render_prompt(spec)
    assert "Topic briefs" in prompt
    assert "summary_only" in prompt


def test_section_draft_prompt_includes_topic_briefs() -> None:
    prompt = section_draft_prompt(
        WorkbenchContext(
            project_id="proj-1",
            request="Draft zoning section.",
            workflow="section_draft",
            active_section_id="zoning",
            topic_briefs=(
                TopicBrief(
                    topic_id="overlay_modifiers",
                    label="Overlay modifiers",
                    status="partial",
                    summary="Overlay rules may modify base standards.",
                ),
            ),
        )
    )
    assert "overlay_modifiers" in prompt
    assert "Overlay modifiers" in prompt
