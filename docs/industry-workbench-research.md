# Industry Workbench Research

## Purpose

This document captures lessons from modern analytical workbenches with agentic support
and translates them into Civil AI product principles.

## Research Lens

A workbench is a browser application where analysts can:

- Discover and select governed data.
- Filter, query, and investigate it.
- Create tables, cohorts, visualizations, calculations, or findings.
- Save and share an investigation.
- Take or recommend an operational action.

The strongest agent integrations are not generic chatbots. They understand workbench
context and produce artifacts that analysts can inspect, edit, save, and act on.

## Product Patterns Reviewed

| Workbench | Strongest pattern | Civil AI lesson |
| --- | --- | --- |
| Palantir Workshop + AIP Analyst | Agent embedded in operational app with access to current objects, datasets, documents, functions, and approved actions. | Use project/entity context, governed object model, visible traces, and approval-gated actions. |
| Hex | Conversation becomes an editable analytical project across chat, notebook, charts, and published app. | Turn agent output into editable investigation artifacts, not isolated answers. |
| Databricks Apps + Genie | Domain-specific conversational analytics grounded in curated lakehouse data and embeddable apps. | Create domain spaces around section facts, jurisdiction, and source coverage; evaluate with real questions. |
| Snowflake Cortex Analyst/Agents | API-first semantic text-to-SQL and tool orchestration for custom frontends. | Separate structured fact retrieval from multi-step agent orchestration. Keep contracts API-first. |
| Microsoft Fabric + Copilot/Data Agents | AI support across notebooks, pipelines, warehouses, BI, and automation. | Distinguish read-only investigation from gated automation. Carry context across data lifecycle. |
| Sigma Assistant | Agent-created analyses and charts move into workbook-style exploration with analysis breakdown. | Show reasoning breakdowns and allow generated outputs to become editable workbench components. |
| Looker Conversational Analytics | Semantic-model grounding and governed query composition. | Treat the BE fact catalog as a semantic layer so users ask business questions, not table questions. |
| Dataiku Agent Hub | Governed multi-agent catalog with sources, tool activity, human approval, and downloadable outputs. | Use internal specialist tools, visible source/tool activity, and human-in-loop governance. |
| Tableau Agent | Natural-language assistance embedded in authoring and dashboard exploration. | Put assistance where analysts are already working: maps, sections, sources, and drafts. |

## Borrowable Patterns

### Context Awareness

The agent should know the active project, entity, selected section, selected artifact,
map layers, filters, source documents, and user role.

### Artifact Creation

The agent should create workbench artifacts:

- Findings.
- Risk items.
- Draft report sections.
- Source bundles.
- Permit checklists.
- Exhibit references.
- Data gaps.
- Recommended actions.

### Transparency

Users should see:

- Sources used.
- Tool activity.
- Derived rules.
- Generated queries or filters.
- Missing data.
- Confidence/status.

### Action Support

The agent can recommend actions, but mutating or external actions require approval.

### Embeddability

Agent output should be embeddable in the main workspace, not trapped in a chat panel.

## Patterns To Avoid

- Floating chatbot with no current project context.
- A single unrestricted agent over the entire data lake.
- Narrative answers without source records or underlying query.
- Charts/tables/findings that cannot be edited or saved.
- Agent-generated actions that execute immediately.
- Exposing a confusing catalog of specialist agents to ordinary users.
- Making users restate current entity, section, and filters in every prompt.
- Treating chat history as the system of record.

## Civil AI Recommendation

Use one visible Civil Analyst Agent, backed by many internal specialist tools.

Make the central workspace the durable artifact surface. Make the right panel the
conversation and command surface. Make the left panel the resource/source surface.

The resulting experience should feel like working with a senior feasibility analyst who
can investigate, explain, draft, cite, and hand off structured work for review.
