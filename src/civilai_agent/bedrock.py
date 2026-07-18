"""Bedrock model configuration for Strands."""

from __future__ import annotations

from strands.models import BedrockModel

from civilai_agent.config import settings


def default_bedrock_model_id() -> str:
    """Model id from CIVILAI_BEDROCK_MODEL_ID, defaulting to Haiku 4.5."""
    return settings().bedrock_model_id.strip()


def build_bedrock_model(*, temperature: float = 0.2, model_id: str | None = None) -> BedrockModel:
    """Build a Strands BedrockModel in the configured AWS region."""
    return BedrockModel(
        model_id=model_id or default_bedrock_model_id(),
        region_name=settings().aws_region.strip(),
        temperature=temperature,
    )
