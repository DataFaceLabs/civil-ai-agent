# Workbench Integration

## Purpose

The frontend workbench is the agent's operating environment. The agent should be aware
of the current project, selected entity, active report section, map layers, source
documents, saved artifacts, and review state.

The agent should not behave like a floating chatbot.

## Recommended Layout

```text
┌────────────────────────────────────────────────────────────────────┐
│ Project / entity / snapshot / freshness / save state                │
├───────────────┬──────────────────────────────────┬─────────────────┤
│ Resources     │ Main analytical workspace         │ Civil Analyst   │
│               │                                  │ Agent           │
│ Data facts    │ Map / table / section / exhibit  │ Context chips   │
│ Source docs   │ Findings and risks               │ Suggested tasks │
│ Saved views   │ Draft report sections            │ Conversation    │
│ Artifacts     │ Review and approval state         │ Sources/steps   │
│ Reports       │ Generated artifacts               │ Add to workspace│
└───────────────┴──────────────────────────────────┴─────────────────┘
```

The right panel is the conversation and command surface. Durable outputs should appear
in the center workspace.

## Workbench Context Envelope

Every agent call should include structured context:

```json
{
  "project": {
    "project_id": "proj_123",
    "name": "Howard Lane Feasibility",
    "snapshot_date": "2026-06-15",
    "proposed_use": "commercial warehouse"
  },
  "entity": {
    "entity_id": "ent_456",
    "address": "2121 W Howard Ln, Austin, TX",
    "parcel_ids": ["..."]
  },
  "workspace": {
    "active_section_id": "utilities",
    "selected_artifact_ids": ["risk_utility_capacity"],
    "selected_source_ids": ["src_tceq_ccn"],
    "selected_map_layers": ["utility_ccn", "fema_nfhl"],
    "visible_filters": {}
  },
  "user": {
    "role": "analyst",
    "permissions": ["draft", "save_artifact"]
  }
}
```

## Agent Output Types

The agent should return one or more of these workbench-native outputs:

| Output | Description |
| --- | --- |
| `message` | Short conversational response. |
| `finding` | Source-backed factual or interpretive finding. |
| `risk` | Constraint with severity, source support, and next action. |
| `draft_section` | ATX Civil style report language. |
| `source_bundle` | Evidence packet used to support an output. |
| `permit_checklist` | Required/likely approvals and dependencies. |
| `data_gap` | Missing, partial, ambiguous, or unavailable field. |
| `recommended_action` | Operational next step, with approval requirement. |
| `query_or_filter` | Inspectable generated query, filter, or map-layer selection. |
| `qa_result` | Unsupported claim, inconsistency, stale source, or caveat issue. |

## Response Actions

Useful user actions include:

- Add finding to section.
- Add citation to artifact.
- Add exhibit reference.
- Save result set.
- Apply filters.
- Open generated query.
- Create comparison/cohort.
- Draft section.
- Revise selected section.
- Create risk item.
- Create permit checklist.
- Mark for SME review.
- Export source bundle.
- Create recommended action, approval required.

## Artifact Lifecycle

### Observe

The agent reads the current project/entity/workspace context.

### Explain

The agent explains known facts, status, uncertainty, and source support.

### Investigate

The agent uses BE facts, provenance, uploaded docs, live source tools, or derivation
tools to answer the user's intent.

### Create Artifact

The agent creates a structured artifact with claims, sources, assumptions, gaps, and
recommended actions.

### Validate

The agent surfaces trace, source support, confidence/status, and missing information.

### Act

The agent recommends actions. Mutating or external actions require approval.

### Save/Share

The user saves the artifact into the project. The artifact, not the chat, becomes the
record.

## Review States

Artifacts should support these states:

| State | Meaning |
| --- | --- |
| `draft` | Created by agent or analyst, not yet reviewed. |
| `needs_evidence` | Contains unsupported or incomplete claims. |
| `needs_sme_review` | Requires professional judgment. |
| `approved` | Approved for use in work product. |
| `rejected` | Rejected with reason. |
| `superseded` | Replaced by a newer artifact or source snapshot. |

## UI Principles

- Users should not need to restate the current parcel, filters, or section.
- Sources and steps should be visible without overwhelming the main reading flow.
- Agent charts/tables/maps should be editable or addable to the workspace.
- Generated section text should be tied to source claims and review state.
- The agent should suggest next investigations based on gaps and risks.
- A source or artifact should be openable from any generated claim.
- The center workspace should remain the durable work surface.

## What The FE Eventually Needs To Persist

Even if the current FE is POC/localStorage, the hardened workbench will need durable
storage for:

- Project metadata.
- Resolved entity and snapshot.
- Proposed use/development program.
- Uploaded source documents.
- Exhibit manifest.
- Saved findings.
- Saved risks.
- Permit checklist.
- Draft report sections.
- User edits.
- SME review decisions.
- Source bundles.
- Export history.

## Anti-Patterns

- Floating chatbot with no workbench context.
- Narrative answers with no sources or generated query.
- Agent output that cannot be saved, edited, or inspected.
- Immediate execution of external actions.
- Treating conversation history as the project record.
- Exposing internal specialist-agent complexity to ordinary users.
- Making every user prompt include parcel, jurisdiction, and filters.
