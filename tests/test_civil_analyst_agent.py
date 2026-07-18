"""Toolset guards for the legacy Civil Analyst agent."""

from __future__ import annotations

from civilai_agent.agents.civil_analyst import build_civil_analyst_agent


def test_legacy_agent_excludes_get_site_payload() -> None:
    """Cost fix (2026-07-16): get_site_payload returns the full multi-section FE
    SitePayload (~30k tokens for a real entity). The Strands tool loop resends every
    tool result on each subsequent turn, so a single get_site_payload call compounded
    into tens of thousands of input tokens per draft -- the dominant driver of the
    2026-07 cost spike. A single-section draft only needs its own section facts plus
    determinations, so the tool must not be in this agent's toolset."""
    agent = build_civil_analyst_agent()
    assert "get_site_payload" not in agent.tool_names


def test_legacy_agent_keeps_targeted_data_tools() -> None:
    """The targeted, active-section tools the draft actually needs stay available."""
    agent = build_civil_analyst_agent()
    for expected in ("get_section_facts", "run_determinations", "resolve_parcel"):
        assert expected in agent.tool_names
