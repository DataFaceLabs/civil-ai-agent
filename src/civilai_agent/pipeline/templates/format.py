"""Shared markdown structure for template-path (no-LLM) section renders.

Template-tier branches (e.g. a rural parcel's zoning, an Edwards-outside environmental)
return deterministic Python-built prose without an LLM call -- good for cost and control,
but historically they emitted flat, unheaded paragraphs. That left a formatting gap: a
City-of-Austin parcel's zoning section came back with markdown headings while a rural
parcel's came back as one bare sentence. This helper gives template output the same
heading structure the LLM render path produces, so every section reads consistently. The
format-parity gate test enforces that no section renders as flat prose.
"""

from __future__ import annotations


def headed_section(section_title: str, blocks: list[tuple[str, str]]) -> str:
    """Build a markdown section: an h1 title over h2 subsections.

    ``blocks`` is a list of ``(subsection_heading, body)`` pairs; pairs with an empty body
    are skipped so optional subsections (e.g. a watershed paragraph that is not present)
    do not leave a dangling heading.
    """
    parts = [f"# {section_title}"]
    for heading, body in blocks:
        if body and body.strip():
            parts.append(f"## {heading}\n\n{body.strip()}")
    return "\n\n".join(parts)
