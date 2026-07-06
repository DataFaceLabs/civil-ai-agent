"""Tests for OpenAI model parameter wiring."""

from civilai_agent.openai_model import openai_model_params


def test_gpt5_omits_temperature() -> None:
    assert openai_model_params(model_id="gpt-5", temperature=0.2) == {}
    assert openai_model_params(model_id="gpt-5.2-pro", temperature=0.2) == {}


def test_gpt4o_keeps_temperature() -> None:
    assert openai_model_params(model_id="gpt-4o", temperature=0.2) == {"temperature": 0.2}
