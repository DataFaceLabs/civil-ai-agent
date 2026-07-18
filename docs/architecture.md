# Architecture

## Status

This is a target design, not an implementation commitment.

The architecture should be stable at the product-contract level before we lock into a
specific agent runtime. AgentCore and Strands are strong candidates, but the first
design priority is defining durable boundaries among the frontend workbench, agent
service, tool layer, backend data platform, artifact store, and evaluation system.

## Design Principles

- `civil-ai-data` remains the source of truth for governed data facts, entity resolution,
  service views, provenance, parcel snapshots, and exports.
- `civil-ai-fe` remains the user-facing workbench for project state, review, editing,
  maps, sections, exhibits, and approvals.
- `civil-ai-agent` owns reasoning, tool orchestration, artifact creation, explanation,
  and QA behavior.
- The agent should not query arbitrary S3 objects directly in the normal product path.
  It should use BE APIs and approved tools that preserve source status and provenance.
- Chat is not the system of record. Saved artifacts are.
- Every generated artifact must be inspectable.

## Target System

```text
┌────────────────────────────────────────────────────────────────────┐
│ civil-ai-fe workbench                                               │
│ project, map, sections, docs, exhibits, review, approval            │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ workbench context + user request
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│ civil-ai-agent API                                                  │
│ context adapter, auth boundary, artifact response contract          │
├────────────────────────────────────────────────────────────────────┤
│ Orchestration layer                                                 │
│ candidate: Strands, graph workflow, or custom planner               │
├────────────────────────────────────────────────────────────────────┤
│ Tool layer                                                          │
│ BE facts, provenance, source retrieval, document search, drafting,  │
│ QA, artifact creation, approved actions                             │
├────────────────────────────────────────────────────────────────────┤
│ Runtime layer                                                       │
│ candidate: AWS AgentCore, container service, or serverless API       │
├────────────────────────────────────────────────────────────────────┤
│ Trace, eval, policy, and artifact persistence adapters              │
└──────────────┬───────────────────────────────┬─────────────────────┘
               │                               │
               ▼                               ▼
┌──────────────────────────────┐   ┌─────────────────────────────────┐
│ civil-ai-data                 │   │ Approved external/source tools   │
│ entity, facts, provenance,    │   │ code text, public portals, docs, │
│ parcel snapshots, exports     │   │ uploaded files, search/retrieval │
└──────────────────────────────┘   └─────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────────────────────────┐
│ S3 data lake and serving layer                                      │
│ source/raw -> curated parquet -> current relations -> svc_section_* │
└────────────────────────────────────────────────────────────────────┘
```

## Backend Boundary

The agent should treat BE APIs as the governed data contract.

Known BE surfaces that matter to the agent:

| Capability | BE surface |
| --- | --- |
| Resolve address or parcel to entity | `/v1/entities/resolve` |
| Fetch one section's facts | `/v1/sections/{section_id}/facts/{entity_id}` |
| Fetch all facts for an entity | `/v1/entities/{entity_id}/facts` |
| Inspect provenance | `/v1/entities/{entity_id}/provenance` |
| Export entity evidence | `/v1/entities/{entity_id}/export` |
| Create and retrieve parcel snapshots | `/v1/parcel-snapshots`, `/v1/parcel-snapshots/{id}` |
| Export parcel snapshot | `/v1/parcel-snapshots/{id}/export` |
| FE site lookup by address or parcel | `/v1/fe/site/by-address`, `/v1/fe/site/by-parcel` |
| Catalog/schema discovery | `/v1/catalog/*` |
| Legacy report workflow | `/report`, `/report/{run_id}`, `/report/{run_id}/domain/{n}` |

The agent should prefer the `/v1` entity/parcel-snapshot/facts/provenance APIs for new design.
The older `/report` flow can remain a compatibility path until the team retires it.

## S3 And Medallion Alignment

The data platform uses a medallion-style architecture:

```text
source/raw inputs -> curated datasets -> current relations -> service views -> APIs
```

The agent should care about the service and API layers rather than raw storage layout.
When the agent needs freshness or lineage, it should request provenance and snapshot
metadata through BE rather than bypassing BE.

## Frontend Boundary

The FE should not send vague prompts alone. It should send a workbench context envelope:

```json
{
  "project_id": "proj_123",
  "entity_id": "ent_456",
  "snapshot_date": "2026-06-15",
  "active_section_id": "utilities",
  "selected_artifact_ids": ["finding_1"],
  "selected_source_ids": ["fema_nfhl"],
  "selected_map_layers": ["fema_nfhl", "ccn_water"],
  "proposed_use": "commercial warehouse",
  "user_role": "analyst",
  "request": "Draft the utility availability finding."
}
```

The agent response should return structured artifacts and UI actions, not only natural
language.

## Agent Response Contract

The frontend should be able to render an agent response as a durable workbench update.

```json
{
  "message": "Wastewater coverage is known, but capacity is not confirmed.",
  "artifacts": [
    {
      "type": "finding",
      "title": "Wastewater service requires provider confirmation",
      "status": "partial",
      "section_id": "utilities",
      "claims": [
        {
          "text": "The site is within a wastewater provider service area.",
          "source_refs": ["src_utility_ccn_1"]
        }
      ],
      "data_gaps": [
        "Nearest public wastewater main and capacity are not available."
      ],
      "recommended_actions": [
        {
          "label": "Confirm capacity with provider",
          "approval_required": true
        }
      ]
    }
  ],
  "trace_summary": {
    "tools_used": ["get_section_facts", "get_entity_provenance"],
    "sources_used": ["tceq_ccn"]
  }
}
```

## Runtime Options

### AWS AgentCore

AgentCore is a strong fit if the team wants an AWS-native managed runtime with IAM
integration, session handling, managed tool execution, centralized audit logging, and
operational controls.

Use AgentCore if:

- The agent will run in AWS alongside the data platform.
- IAM isolation and CloudWatch-style audit are important early.
- The team wants managed session/tool infrastructure.
- We expect multiple agent entry points or future external integrations.

Watch-outs:

- Keep business logic out of runtime-specific glue.
- Do not make FE or BE contracts depend on AgentCore-specific concepts.
- Confirm support for trace export, human approval flows, and artifact persistence.

### Strands

Strands is a strong fit if we need explicit orchestration over multi-step research and
drafting workflows.

Use Strands if:

- We want tool routing, planning, and specialized workflows to be declared explicitly.
- We need repeatable section-generation workflows.
- We want clear separation between planning, retrieval, drafting, QA, and action
  recommendation.

Watch-outs:

- Keep tool contracts framework-agnostic.
- Avoid hiding product policy inside prompt-only behavior.
- Ensure traces are visible to the workbench and evaluation harness.

### Custom Agent Service

A custom service may be enough for early phases if the first product surfaces are narrow:

- Retrieve facts.
- Draft section.
- Run QA.
- Save artifact.

This path may reduce initial complexity, but it can become harder to govern if tool and
approval flows grow quickly.

## Recommended Architecture Decision

Design framework-independent contracts now:

- Workbench context envelope
- Tool schemas
- Artifact schemas
- Source/provenance contract
- Approval policy
- Trace/evaluation contract

Prototype AgentCore + Strands behind those contracts. Treat them as replaceable
implementation choices until we validate:

- Developer ergonomics
- Trace quality
- Runtime observability
- Tool policy enforcement
- Human approval flow
- Cost and latency

## Context And Memory

The agent should maintain short-lived conversational context, but durable memory belongs
to project artifacts.

Durable project state should include:

- Project metadata
- Resolved entity and snapshot date
- Proposed use
- Saved findings
- Saved risks
- Saved source bundles
- Draft sections
- User/SME notes
- Review statuses
- Exports

Conversation history can help the next turn, but it should never be the only place where
a decision or finding exists.

## Security And Governance

- Use read-only BE data access for investigation tools.
- Require explicit user approval for mutating actions.
- Log tool calls, source IDs, prompts, generated artifacts, and approval events.
- Preserve BE source status values such as complete, partial, ambiguous, unavailable,
  not_applicable, and insufficient_data.
- Do not allow unrestricted data lake access from the agent.
- Enforce user/project permissions at the workbench and agent API boundary.

## Open Decisions

- Whether AgentCore is the initial runtime or a later hardening target.
- Whether Strands is used for all orchestration or only complex workflows.
- Where artifact persistence lives before the FE is hardened.
- Whether source document retrieval uses a dedicated document index or BE-managed
  document APIs.
- How live public source lookups are rate-limited, cached, and provenance-stamped.
- Which actions are allowed in POC, pilot, and production modes.
