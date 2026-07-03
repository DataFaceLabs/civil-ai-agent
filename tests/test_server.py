"""Tests for the dev-only HTTP wrapper (server.py).

Mocks run_agent so this never makes a real (billed) Bedrock call.
"""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from civilai_agent.models.context import AgentResponse, TraceSummary, WorkbenchContext
from civilai_agent.server import app

client = TestClient(app)


def test_healthz() -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_run_returns_agent_response() -> None:
    fake_response = AgentResponse(
        message="Preliminary finding.",
        trace_summary=TraceSummary(tools_used=("get_section_facts",)),
    )
    with patch("civilai_agent.server.run_agent", return_value=fake_response) as mock_run:
        resp = client.post(
            "/v1/agent/run",
            json={"project_id": "local-dev", "request": "What is the FEMA flood zone?"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["message"] == "Preliminary finding."
    assert body["trace_summary"]["tools_used"] == ["get_section_facts"]
    called_context = mock_run.call_args.args[0]
    assert isinstance(called_context, WorkbenchContext)
    assert called_context.request == "What is the FEMA flood zone?"


def test_run_passes_dry_run_flag() -> None:
    fake_response = AgentResponse(message="[dry-run]")
    with patch("civilai_agent.server.run_agent", return_value=fake_response) as mock_run:
        resp = client.post(
            "/v1/agent/run?dry_run=true",
            json={"project_id": "local-dev", "request": "test"},
        )
    assert resp.status_code == 200
    assert mock_run.call_args.kwargs["dry_run"] is True


def test_run_rejects_missing_request_field() -> None:
    resp = client.post("/v1/agent/run", json={"project_id": "local-dev"})
    assert resp.status_code == 422
