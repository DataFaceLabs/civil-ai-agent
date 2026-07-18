"""Dev-only HTTP wrapper around run_agent() for local UAT.

There is no way to exercise the agent from the frontend today: the FE's main
create/draft flow never calls it, the only wired path (AgentPanel -> civil-ai-platform)
targets a service that has no runnable code yet, and civil-ai-agent itself has never
exposed an HTTP endpoint (CLI-only). This module unblocks local UAT (comparing agent
output against real client feasibility studies) without waiting on the full platform
build-out.

NOT FOR PRODUCTION. No auth, no rate limiting, no tenant isolation -- any request
triggers a real (billed) Bedrock call. Local development only, matching the project's
existing rule that dev-environment work needs no extra sign-off (unlike a value trusted
in a delivered client study). Requires the optional `serve` dependency group:
`uv pip install -e ".[serve]"`.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from civilai_agent.models.context import AgentResponse, WorkbenchContext
from civilai_agent.runner import run_agent

app = FastAPI(title="civilai-agent (dev-only)")

# Local Vite dev server only. This app has no auth, so it must never be exposed beyond
# localhost -- CORS is scoped accordingly rather than left open.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["POST"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/agent/run", response_model=AgentResponse)
def run(context: WorkbenchContext, dry_run: bool = False) -> AgentResponse:
    return run_agent(context, dry_run=dry_run)
