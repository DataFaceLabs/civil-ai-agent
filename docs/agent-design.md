# Agent Design

## Purpose

The Civil AI Agent supports analysts preparing land-development feasibility studies. It
helps turn structured backend facts, public source evidence, uploaded customer
documents, SME assumptions, and frontend workbench context into reviewed feasibility
artifacts.

The agent should help answer questions such as:

- What is known about this site?
- Which constraints materially affect the proposed development?
- What evidence supports each finding?
- What is missing or uncertain?
- What should the analyst do next?
- Which report language can be drafted from the current evidence?

## Goals

- Reduce the time required to research and draft a feasibility study.
- Preserve the analyst's professional judgment and review responsibility.
- Make every factual claim inspectable through source records, BE provenance, uploaded
  documents, or explicit user assumptions.
- Create reusable artifacts, not disposable chat answers.
- Help analysts find gaps early, especially utility capacity, OSSF feasibility,
  floodplain risk, jurisdiction ambiguity, platting status, ROW/access constraints,
  title/easement issues, and permitting dependencies.
- Align generated language with the ATX Civil template while supporting justified SME
  deviations.
- Produce outputs that can later be hardened into authenticated, durable frontend
  workflows.

## Non-Purpose

The agent is not:

- A PE replacement or autonomous signer.
- A legal opinion engine.
- A permitting authority.
- A source of utility capacity or will-serve determinations.
- A generic chatbot over the data lake.
- A tool that silently executes operational actions.
- A report generator that treats the template as a rigid form.
- A system of record for approved findings; saved artifacts are the system of record.

## Users

### Analyst

Primary daily user. Builds the project, investigates facts, drafts sections, edits
language, and marks outputs ready for SME review.

### SME / Civil Engineer

Reviews findings, resolves judgment calls, approves report language, and determines
whether a project is feasible, feasible with conditions, constrained, or infeasible.

### Reviewer / QA

Checks source support, consistency, section completeness, and whether caveats are strong
enough for customer delivery.

### Customer-Facing Stakeholder

Consumes final findings and recommendations, but should not need to interact directly
with internal agent traces.

## Product Principles

### Artifact Lifecycle Over Chat

The agent should follow this loop:

```text
observe -> explain -> investigate -> create artifact -> validate -> act -> save/share
```

Chat can initiate work, but important outputs must become structured artifacts:

- Site finding
- Constraint or risk item
- Source citation
- Exhibit reference
- Permit checklist item
- Report section draft
- Data gap
- SME assumption
- Recommended next action

### One Visible Agent, Many Internal Tools

Ordinary users should see one contextual Civil Analyst Agent. Internally, the agent may
route work to specialist tools or sub-agents for parcel, zoning, flood, utilities,
environmental review, report drafting, QA, or source retrieval.

The UI should not expose a confusing catalog of agents unless the user is in an
administrative or debugging mode.

### Governed Data First

The agent should use backend service facts and provenance first. Live source tools and
uploaded documents supplement the backend when the data platform does not yet contain a
needed field.

### Inspectability Is A Feature

Every generated artifact should expose:

- Inputs used
- Source records used
- Tool calls or retrieval steps
- Derived rules
- Assumptions
- Confidence/status
- Missing information
- Whether SME review is required

### No Silent Operational Actions

The agent may recommend actions. Actions that create, send, submit, mutate, or contact
external systems require explicit approval.

Examples requiring approval:

- Create external case/action
- Send email to utility provider
- Submit form or request
- Change project status
- Mark report section approved
- Export customer-facing deliverable

## Capability Modes

### 1. Contextual Q&A

Answer questions about the current project, selected parcel, active section, map layer,
source document, or saved artifact.

Example:

```text
Is this site in a FEMA floodplain, and what does that mean for the proposed use?
```

Expected behavior:

- Use current project/entity context.
- Retrieve flood facts and provenance.
- Explain the operational implication.
- Distinguish known facts from required follow-up.

### 2. Guided Investigation

Help the analyst perform a structured investigation across multiple sources.

Example:

```text
Check whether wastewater service is a feasibility blocker.
```

Expected behavior:

- Retrieve utility provider/service facts.
- Identify whether line distance/capacity data is present.
- Apply OSSF and extension caveats.
- Create a data gap if capacity or public main location is unknown.
- Recommend next steps.

### 3. Artifact Creation

Create a structured output that can be added to the workbench.

Examples:

- Draft Section 3.5 Utility Location and Availability.
- Create a risk item for OSSF infeasibility.
- Add a source-backed finding to Watershed.
- Build a permit checklist for the proposed development.

### 4. Review and QA

Inspect an existing artifact for unsupported claims, stale sources, weak caveats,
internal inconsistencies, or template misalignment.

Example:

```text
Review the floodplain section for unsupported claims and missing citations.
```

### 5. Action Recommendation

Recommend next operational actions without executing them automatically.

Examples:

- Request fire flow test.
- Confirm utility capacity with provider.
- Order current boundary survey.
- Search title commitment for easements.
- Schedule pre-application meeting.
- Confirm TxDOT driveway permit applicability.

## Core Artifacts

### Finding

A concise, source-backed statement about the site.

Examples:

- The property is in Travis County and City of Austin ETJ.
- The FEMA flood fact is unavailable for the current entity.
- Wastewater provider coverage is known, but capacity is not confirmed.

### Constraint

A condition that limits development or requires design response.

Examples:

- Critical Water Quality Zone affects developable area.
- OSSF minimum lot size may block subdivision.
- TxDOT frontage introduces driveway permit dependency.

### Risk Item

A constraint with severity, likelihood, source support, and recommended follow-up.

### Permit Checklist Item

A required or likely approval, tied to jurisdiction, proposed use, source rule, owner,
status, and dependency.

### Report Section Draft

Narrative language in ATX Civil voice, backed by facts, citations, caveats, and
review state.

### Source Bundle

The collection of source records, URLs, documents, map layers, and BE provenance used to
support an artifact.

### Exhibit Manifest

A structured list of exhibits used or expected in the study, including maps, surveys,
FIRM panels, watershed exhibits, soils maps, utility maps, and site layouts.

## Required Context From The Workbench

The agent should receive a project context envelope rather than asking the user to
restate the basics:

```json
{
  "project_id": "proj_123",
  "entity_id": "ent_456",
  "snapshot_date": "2026-06-15",
  "active_section_id": "utilities",
  "selected_artifact_ids": ["finding_1", "risk_3"],
  "selected_map_layers": ["fema_nfhl", "utilities_ccn"],
  "proposed_use": "commercial warehouse",
  "jurisdiction_summary": {
    "county": "Travis",
    "primary_jurisdiction": "City of Austin ETJ",
    "service_coverage": "partial"
  },
  "user_role": "analyst"
}
```

## Guardrails

- Do not invent facts.
- Do not infer capacity from service territory.
- Do not state legal conclusions.
- Do not use conversation history as the only record of a decision.
- Do not draft customer-facing certainty when source status is partial, ambiguous, or
  unavailable.
- Do not treat the template as rigid when real feasibility logic requires a different
  section order or emphasis.
- Do not hide missing data; surface it as a first-class data gap.

## Success Measures

- Analysts can create a source-backed first-pass investigation faster.
- SMEs can inspect and correct agent outputs without reverse-engineering how they were
  produced.
- Section drafts require less manual rework over time.
- Unsupported claims decline in QA review.
- Data gaps are found earlier in the workflow.
- Saved artifacts become reusable project knowledge, independent of chat history.
