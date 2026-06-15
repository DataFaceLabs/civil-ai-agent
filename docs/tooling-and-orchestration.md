# Tooling And Orchestration

## Purpose

This document defines the agent tool model before implementation. It separates product
behavior from any specific framework such as AgentCore or Strands.

## Tooling Principles

- Tools return structured data, source references, status, and errors.
- Tools should be scoped by project/entity/user permissions.
- Tools should preserve BE provenance and source freshness.
- Tools should distinguish facts, derivations, assumptions, and generated language.
- Tools that mutate state or contact external systems require explicit approval.
- Tools should be testable outside a live chat session.

## Tool Categories

### 1. Backend Fact Tools

Read governed BE data.

Examples:

- Resolve address or parcel to entity.
- Fetch section facts.
- Fetch all entity facts.
- Fetch provenance.
- Export entity/project evidence.
- Read catalog metadata.

### 2. Source Retrieval Tools

Retrieve public source or uploaded document content not yet available in BE.

Examples:

- Fetch code/manual section.
- Search uploaded feasibility docs.
- Search title/survey/customer files.
- Retrieve public GIS/source metadata.

### 3. Derivation Tools

Apply explicit rules to source-backed facts.

Examples:

- Determine controlling impervious cover limit.
- Determine whether OSSF lot-size threshold is met.
- Determine likely TxDOT driveway permit dependency.
- Determine permit checklist candidates.

Derivation tools must return:

- Input facts.
- Rule used.
- Citation.
- Result.
- Confidence/status.

### 4. Drafting Tools

Generate report language or workbench text from structured evidence.

Examples:

- Draft section.
- Summarize source bundle.
- Rewrite section in ATX Civil voice.
- Produce customer-facing summary.

Drafting tools should not create unsupported facts. They should consume facts,
citations, assumptions, and data gaps produced by other tools.

### 5. QA Tools

Inspect artifacts for quality and risk.

Examples:

- Find unsupported claims.
- Check citations.
- Compare section draft against source facts.
- Check template completeness.
- Flag overclaiming or weak caveats.
- Detect contradiction across sections.

### 6. Artifact Tools

Create, update, or save workbench artifacts.

Examples:

- Add finding.
- Add risk.
- Add source citation.
- Add exhibit reference.
- Save draft section.
- Mark for SME review.

These are mutating tools and should require user intent. Some may require explicit
approval depending on workflow state.

### 7. External Action Tools

Initiate work outside the project record.

Examples:

- Create provider inquiry.
- Send email.
- Submit request.
- Create task in another system.
- Export final customer-facing packet.

These always require explicit approval.

## Internal Specialist Tools

The product should expose one visible Civil Analyst Agent. Internally, orchestration may
route to specialist tools:

| Specialist | Responsibilities |
| --- | --- |
| Parcel Analyst | Entity resolution, parcel identity, CAD context, acreage caveats. |
| Jurisdiction Analyst | City/county/ETJ/fire/utility authorities and source routing. |
| Zoning Analyst | Zoning, overlays, use fit, compatibility, rezoning risk. |
| Watershed/Flood Analyst | Watershed, FEMA, CWQZ, Edwards, drainage criteria. |
| Utility Analyst | Provider coverage, OSSF risk, capacity gaps, fire flow. |
| Mobility Analyst | ROW, access, road authority, TxDOT, sidewalks, TIA. |
| Document Analyst | Uploaded docs, title, survey, prior reports, exhibit references. |
| Report Drafter | ATX Civil narrative generation from evidence. |
| QA Reviewer | Unsupported claims, caveats, citations, contradictions. |

## Approval Classes

| Class | Examples | Approval |
| --- | --- | --- |
| Read | Fetch facts, provenance, source docs | No explicit approval after user request. |
| Analyze | Derive IC limit, identify risk, compare facts | No explicit approval after user request. |
| Draft | Draft section, summarize source bundle | User intent required. |
| Save | Add artifact, update section draft | User action required. |
| Review state | Mark approved/rejected/needs SME | Role-gated approval required. |
| External action | Send request, create case, submit form | Explicit approval required. |

## Standard Tool Result Shape

```json
{
  "tool_name": "get_section_facts",
  "status": "ok",
  "entity_id": "ent_456",
  "section_id": "utilities",
  "snapshot_date": "2026-06-15",
  "facts": {},
  "source_refs": [],
  "data_status": "partial",
  "data_gaps": [],
  "warnings": [],
  "trace": {
    "duration_ms": 420,
    "request_id": "req_abc"
  }
}
```

## Orchestration Patterns

### Minimal Retrieval

For direct questions, call the smallest set of tools needed and answer with citations.

### Section Drafting

1. Fetch relevant BE facts.
2. Fetch provenance.
3. Retrieve needed source/rule text.
4. Apply derivations.
5. Draft section.
6. Run QA.
7. Return draft plus citations, gaps, and recommended actions.

### Gap Analysis

1. Fetch all entity facts.
2. Compare to section playbooks.
3. Classify missing values as backend gap, source lookup, user input, or not applicable.
4. Create data gaps and recommended actions.

### QA Review

1. Parse claims in artifact.
2. Link each claim to facts/sources.
3. Flag unsupported or overstated claims.
4. Check for required caveats.
5. Return actionable corrections.

## Prompt/Policy Separation

Do not rely on prompts alone for high-risk behavior.

Hard policies should be enforced by tools or service logic:

- Utility capacity cannot be inferred from CCN/provider coverage.
- Missing facts cannot be filled from model memory.
- Mutating actions require approval.
- Saved artifacts must include source support or explicit assumption labels.
- Role-gated review state changes require permission checks.

## Tracing

Every agent run should produce a trace summary usable by the workbench and evaluation
system:

- User request.
- Workbench context.
- Tools called.
- Sources used.
- Artifacts created.
- Data gaps found.
- Approval requests.
- Errors/warnings.
- Final response.
