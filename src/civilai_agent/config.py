"""Central runtime configuration — every env knob the agent reads, in one place.

Call :func:`settings` at use time, never at import time, and never cache the
result at module level: the eval harness toggles env vars (for example
``CIVILAI_DRAFT_PIPELINE``) between requests, so a cached snapshot would go
stale. Construction is cheap (a handful of ``os.environ`` reads).
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# The tool-loop DataApiClient keeps a short default; the deterministic pipeline
# uses a long one because determinations over Athena can run for minutes. Both
# honor CIVILAI_DATA_API_TIMEOUT when set. Single-sourced here — do not
# re-declare these defaults at call sites.
DATA_API_TIMEOUT_DEFAULT = 30.0
PIPELINE_DATA_API_TIMEOUT_DEFAULT = 180.0


class AgentSettings(BaseSettings):
    """Typed view of the ``CIVILAI_*`` (and related) environment variables."""

    model_config = SettingsConfigDict(env_prefix="CIVILAI_", extra="ignore")

    draft_pipeline: str = ""
    """CIVILAI_DRAFT_PIPELINE — "1" routes section drafts through the pipeline."""

    model_provider: str = "bedrock"
    """CIVILAI_MODEL_PROVIDER — "bedrock" (default) or "openai"."""

    bedrock_model_id: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    openai_model_id: str = "gpt-4o"
    openai_temperature: str = ""
    """CIVILAI_OPENAI_TEMPERATURE — optional override; empty means use caller's."""

    data_api_base: str = "http://localhost:8000"
    platform_data_proxy: str = ""
    data_service_key: str = ""
    data_api_timeout: float | None = None
    """CIVILAI_DATA_API_TIMEOUT — unset means caller-specific default (see above)."""

    web_search_provider: str = "tavily"
    tavily_api_key: str = ""
    web_search_timeout_sec: float = 15.0

    aws_region: str = Field(default="us-east-1", validation_alias="AWS_DEFAULT_REGION")
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")

    @property
    def use_draft_pipeline(self) -> bool:
        """Whether section drafts route through the deterministic pipeline."""
        return self.draft_pipeline.strip() == "1"


def settings() -> AgentSettings:
    """Read the environment fresh and return typed settings (never cached)."""
    return AgentSettings()
