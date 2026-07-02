# civil-ai-agent

Design and implementation home for the Civil AI Agent supporting Project Landmark.

The agent is the AI-assisted analyst layer over the Civil AI data platform and
frontend workbench. Its job is not merely to answer parcel questions. Its job is to
help analysts convert governed parcel, jurisdiction, environmental, utility, code,
document, and exhibit evidence into inspectable feasibility artifacts that can become
draft report sections, risk findings, permit checklists, recommendations, and reviewed
customer deliverables.

## Current Status

**Phase 1 foundation** — design docs plus an initial Strands agent package (`src/civilai_agent/`).

The backend data platform and frontend workbench are under active parallel development;
contracts in this repo stay framework-agnostic so runtime wiring can live in
`civil-ai-platform` (AgentCore) without changing FE shapes.

The design docs answer four questions that guided the first implementation:

1. What problem is the Civil AI Agent solving?
2. What data, source evidence, and workbench context does the agent need?
3. What artifacts should the agent create, save, explain, and revise?
4. Which architecture choices should remain flexible until the contracts are validated?

## Product Principle

The agent participates in the analyst's artifact lifecycle, not just the conversation.

The expected loop is:

```text
observe -> explain -> investigate -> create artifact -> validate -> act -> save/share
```

Conversation is a control surface. The system of record is the structured project
artifact set saved through the workbench.

## Local development

```bash
make install   # uv sync
make test      # pytest
uv run civilai-agent run --request "..." --dry-run --json
```

See `.env.example` for `CIVILAI_DATA_API_BASE` and Bedrock settings.

## Repository Boundaries

`civil-ai-data` owns the data platform:

- S3 data lake and medallion architecture
- Curated parcel, overlay, and reference data
- Service views and API-facing facts
- Entity resolution, section facts, provenance, project snapshots, and exports

`civil-ai-fe` owns the user workbench:

- Project setup and project state
- Analyst workflow surface
- Map, section, source, exhibit, and draft views
- User review, approval, and editing workflows

`civil-ai-agent` owns the agentic layer:

- Agent behavior and product rules
- Tool contracts and orchestration design
- Workbench context envelope
- Artifact schemas
- Citation, provenance, and inspectability rules
- Evaluation strategy
- Strands agent implementation (`civilai_agent` package)

Production **runtime orchestration** (agent-runs API, AgentCore IaC) lives in
`civil-ai-platform`; see meta-repo `docs/decisions/ADR-0003-strands-agentcore.md`.

## Documentation Map

Read the docs in this order:

1. [Agent Design](docs/agent-design.md)
   - Goals, purpose, non-purpose, users, artifacts, capability modes, and guardrails.

2. [Architecture](docs/architecture.md)
   - Target architecture, integration boundaries, AgentCore/Strands decision framing,
     runtime layers, security, and data flow.

3. [Data Alignment](docs/data-alignment.md)
   - How the agent aligns with S3, the backend service views, current BE APIs, section
     facts, provenance, missing fields, and API gaps.

4. [Readiness Gates](docs/readiness-gates.md)
   - Prerequisites for implementation, pilot, and production, including BE data lake
     completeness and validation gates.

5. [Implementation Roadmap](docs/implementation-roadmap.md)
   - Delivery phases, epics, stories, cross-team dependencies, and MVP sequencing.

6. [Workbench Integration](docs/workbench-integration.md)
   - How the agent appears in the frontend workbench, what context it receives, and how
     it creates durable project artifacts.

7. [Tooling and Orchestration](docs/tooling-and-orchestration.md)
   - Tool taxonomy, internal specialist tools, approval classes, and tool result
     contracts.

8. [Template and Section Guidance](docs/template-and-section-guidance.md)
   - How the ATX Civil template should guide the agent, why SMEs deviate, and what each
     feasibility section is meant to accomplish.

9. [Section Playbooks](docs/section-playbooks.md)
   - Detailed per-section drafting and data guidance derived from real feasibility
     studies.

10. [ATX Civil Writing Guide](docs/atx-civil-writing-guide.md)
   - Voice, tone, citation, caveat, and report-writing conventions.

11. [Data Catalog](docs/data-catalog.md)
   - Current summarized field coverage and source status from the backend perspective.

12. [Evaluation Strategy](docs/evaluation-strategy.md)
    - How to test factual grounding, section quality, source traceability, and SME
      acceptance.

13. [Industry Workbench Research](docs/industry-workbench-research.md)
    - Lessons borrowed from Palantir, Hex, Databricks, Snowflake, Fabric, Sigma, Looker,
      Dataiku, and Tableau.

## North Star

Civil AI should feel less like asking a chatbot about land records and more like working
with a senior feasibility analyst who produces inspectable, reusable work product.
