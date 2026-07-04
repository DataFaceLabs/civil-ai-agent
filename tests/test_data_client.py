"""Tests for DataApiClient configuration."""

from civilai_agent.tools.data_client import DataApiClient


def test_data_api_client_timeout_defaults_to_30(monkeypatch) -> None:
    monkeypatch.delenv("CIVILAI_DATA_API_TIMEOUT", raising=False)
    client = DataApiClient(base_url="http://data.test")
    assert client.timeout == 30.0


def test_data_api_client_timeout_from_env(monkeypatch) -> None:
    monkeypatch.setenv("CIVILAI_DATA_API_TIMEOUT", "180")
    client = DataApiClient(base_url="http://data.test")
    assert client.timeout == 180.0


def test_data_api_client_explicit_timeout_overrides_env(monkeypatch) -> None:
    monkeypatch.setenv("CIVILAI_DATA_API_TIMEOUT", "180")
    client = DataApiClient(base_url="http://data.test", timeout=45.0)
    assert client.timeout == 45.0
