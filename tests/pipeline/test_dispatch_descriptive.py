"""Contract tests for descriptive (parcel/access) dispatcher."""

from __future__ import annotations

from civilai_agent.pipeline.dispatch.descriptive import dispatch_descriptive
from civilai_agent.pipeline.fetch import SectionContext


def test_access_row_and_asmp_stems() -> None:
    spec = dispatch_descriptive(
        SectionContext(
            entity_id="ent-1",
            section_id="access",
            facts={
                "facts": {
                    "row_existing_ft": 60.0,
                    "row_required_ft": 70.0,
                    "asmp_level": "Level 2",
                },
                "evidence": {
                    "row_existing_ft": [
                        {
                            "source_name": "ASMP",
                            "source_id": "coa_asmp",
                            "citation_url": "https://example.com/asmp",
                            "as_of": "2026-01-15",
                        }
                    ]
                },
            },
        ),
        "access",
    )
    assert any("existing ROW" in stem and "60" in stem for stem in spec.stems)
    assert any("ASMP" in stem and "Level 2" in stem for stem in spec.stems)
    assert any(c.get("as_of") == "2026-01-15" for c in spec.citations)


def test_parcel_descriptive_has_no_access_stems() -> None:
    spec = dispatch_descriptive(
        SectionContext(
            entity_id="ent-1",
            section_id="parcel",
            facts={"facts": {"row_existing_ft": 60.0}},
        ),
        "parcel",
    )
    assert spec.stems == []
