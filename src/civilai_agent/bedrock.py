"""Bedrock model configuration for Strands."""

from __future__ import annotations

import os

from strands.models import BedrockModel


def default_bedrock_model_id() -> str:
    return os.getenv(
        "CIVILAI_BEDROCK_MODEL_ID",
        "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    ).strip()


def build_bedrock_model(*, temperature: float = 0.2) -> BedrockModel:
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1").strip()
    return BedrockModel(
        model_id=default_bedrock_model_id(),
        region_name=region,
        temperature=temperature,
    )
