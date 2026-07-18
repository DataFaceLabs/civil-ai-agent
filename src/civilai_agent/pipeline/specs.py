"""Draft-spec contracts between deterministic and generative pipeline stages."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MissingInputResolution = Literal["client", "records", "web", "data-gap"]


class MissingInput(BaseModel):
    """An input the SME study used that governed data does not supply."""

    model_config = ConfigDict(extra="forbid")

    name: str
    why_needed: str
    resolution: MissingInputResolution


class DraftSpec(BaseModel):
    """Everything the renderer needs; branch and tier are decided in Python."""

    model_config = ConfigDict(extra="forbid")

    entity_id: str
    section_id: str
    branch_id: str
    tier: int = Field(ge=0, le=3)
    slots: dict[str, str | None] = Field(default_factory=dict)
    facts: dict[str, Any] = Field(default_factory=dict)
    determinations: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    stems: list[str] = Field(default_factory=list)
    missing_inputs: list[MissingInput] = Field(default_factory=list)
    searchable_gaps: list[str] = Field(default_factory=list)

    @field_validator("tier")
    @classmethod
    def tier_in_range(cls, value: int) -> int:
        if value not in range(4):
            msg = "tier must be 0..3"
            raise ValueError(msg)
        return value
