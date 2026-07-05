"""Direct OpenAI model configuration for Strands (alternative to Bedrock)."""

from __future__ import annotations

from strands.models.openai import OpenAIModel

from civilai_agent.config import settings

# Reasoning-tier GPT-5 / o-series models reject non-default temperature (OpenAI 400).
_NO_CUSTOM_TEMPERATURE_PREFIXES = ("gpt-5", "o1", "o3", "o4")


def default_openai_model_id() -> str:
    """Model id from CIVILAI_OPENAI_MODEL_ID, defaulting to gpt-4o."""
    return settings().openai_model_id.strip()


def openai_model_params(*, model_id: str, temperature: float) -> dict[str, float]:
    """Build Strands OpenAIModel params; omit temperature when the model forbids it."""
    if any(model_id.startswith(prefix) for prefix in _NO_CUSTOM_TEMPERATURE_PREFIXES):
        return {}
    override = settings().openai_temperature.strip()
    if override:
        return {"temperature": float(override)}
    return {"temperature": temperature}


def build_openai_model(*, temperature: float = 0.2, model_id: str | None = None) -> OpenAIModel:
    """Build a Strands OpenAIModel for the resolved model id.

    api_key falls through to the openai SDK's own OPENAI_API_KEY env lookup when
    omitted; only pass it explicitly when set so client_args stays empty otherwise.
    """
    resolved_id = model_id or default_openai_model_id()
    api_key = settings().openai_api_key.strip()
    client_args = {"api_key": api_key} if api_key else {}
    return OpenAIModel(
        client_args=client_args,
        model_id=resolved_id,
        params=openai_model_params(model_id=resolved_id, temperature=temperature),
    )
