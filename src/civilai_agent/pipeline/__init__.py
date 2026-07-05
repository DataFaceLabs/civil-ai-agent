"""Deterministic-first section draft pipeline (ADR-0006).

Python orchestrates resolve → fetch → branch dispatch → template/render;
the LLM is a constrained renderer only when tier >= 2.
"""

from civilai_agent.pipeline.specs import DraftSpec, MissingInput

__all__ = ["DraftSpec", "MissingInput"]
