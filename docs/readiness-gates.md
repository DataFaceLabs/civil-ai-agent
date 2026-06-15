# Readiness Gates

## Purpose

This document defines the gates that must be satisfied before the Civil AI Agent can move
from design to implementation, from implementation to pilot, and from pilot to
production.

The most important rule: the agent cannot compensate for unvalidated data. If backend
facts, source status, provenance, or project snapshots are incomplete for the MVP scope,
the agent must remain in design/prototype mode or clearly label those areas as data
gaps.

## Gate 0: Scope Readiness

The team must define the launch scope before implementation.

Required decisions:

- MVP counties and jurisdictions.
- MVP project types or proposed uses.
- MVP report sections.
- Which sections may be draftable vs read-only vs out of scope.
- Which source gaps are acceptable as explicit data gaps.
- Which actions are recommendation-only.

Exit criteria:

- MVP scope is documented.
- Non-MVP areas are documented as out of scope or data gaps.
- SMEs agree the scoped workflow would be useful even with known gaps.

## Gate 1: Backend Data Readiness

The BE data lake must be MVP-complete and validated for the launch scope.

MVP-complete means:

- Required source pulls exist for the scoped geography and sections.
- Curated datasets are populated.
- Current relations are built.
- `svc_section_*` service views are populated.
- `/v1` facts APIs return stable schemas.
- Provenance and status are available for material facts.
- Project snapshots and exports are reproducible.
- Coverage limits are explicit.

Validation checklist:

| Area | Requirement |
| --- | --- |
| Entity resolution | Address and parcel resolution works for representative cases. |
| Section facts | MVP sections return expected fields, statuses, and source refs. |
| Provenance | Material claims can be traced to source records or derivations. |
| Status values | complete, partial, ambiguous, unavailable, not_applicable, and insufficient_data are preserved. |
| Freshness | Snapshot/source date is available where needed. |
| Project snapshots | Project facts are reproducible for the same snapshot date. |
| Exports | Entity/project export contains enough evidence for review. |
| Coverage matrix | Geography and source coverage limits are documented. |

Blocking issues:

- Utility provider coverage is presented as capacity.
- Facts have no provenance.
- Missing facts are returned as complete.
- Snapshot behavior is not reproducible.
- Section schemas change without versioning or catalog metadata.

## Gate 2: Workbench Contract Readiness

The FE and agent must agree on the workbench context and response contracts.

Required contracts:

- Project context envelope.
- Entity ID and snapshot handling.
- Active section/workspace state.
- Selected artifacts and sources.
- Proposed use/development program.
- Agent response shape.
- Artifact types.
- Review states.
- Approval requirements.

Exit criteria:

- FE can send enough context for the agent to avoid asking the user to restate the
  current parcel, section, and selected evidence.
- FE can render at least message, finding, data gap, risk, draft section, source refs,
  and suggested action.
- The team knows where artifacts will be persisted for MVP.

## Gate 3: Agent Foundation Readiness

Before user-facing agent behavior:

- Agent API exists.
- BE tools are implemented.
- Tool results include status, source refs, warnings, and data gaps.
- Trace envelope exists.
- Artifact schemas exist.
- Core policies are enforced in code or tool layer, not prompt only.

Core policies:

- Do not invent facts.
- Do not infer utility capacity from service territory.
- Do not hide missing data.
- Do not create report-ready claims without source support or explicit assumptions.
- Do not execute mutating/external actions without approval.

## Gate 4: Drafting Readiness

Before report section drafting is exposed:

- Section playbooks are reviewed for the MVP sections.
- ATX Civil writing guide is reviewed by SMEs.
- Template deviation guidance is available.
- Golden evaluation cases exist.
- QA checks exist for unsupported claims and utility overclaims.

Exit criteria:

- Drafts include facts, citations/source refs, caveats, data gaps, and recommended
  actions.
- Drafts preserve partial/ambiguous/unavailable status.
- Feasibility posture is supported by section risks and facts.
- QA can block or flag unsafe language.

## Gate 5: Workbench Artifact Readiness

Before saved agent artifacts become project work product:

- Artifact persistence is implemented.
- Saved artifacts retain source refs and trace IDs.
- Review states are role-aware.
- Stale/superseded artifacts can be identified.
- Source bundles can be opened from artifacts.

Exit criteria:

- An analyst can save a finding, risk, data gap, and draft section.
- An SME can review and approve/reject artifacts.
- QA can inspect source support without replaying the chat.

## Gate 6: Approved Action Readiness

Before the agent can initiate external or mutating actions:

- Approval UX exists.
- Role permissions exist.
- Action payload preview exists.
- Action audit log exists.
- Failure/rollback behavior is documented.

External or mutating actions include:

- Sending provider emails.
- Creating external tickets/cases.
- Submitting forms.
- Marking sections approved.
- Exporting customer-facing deliverables.
- Updating project status.

Exit criteria:

- No external action can execute without explicit approval.
- Approval event is traceable to user, project, artifact, and payload.

## Gate 7: Pilot Readiness

Before pilot:

- BE MVP scope is validated.
- FE context and artifact contracts are working.
- Read-only Q&A, findings, gaps, risks, and selected drafts are available.
- QA checks run against generated drafts.
- Golden evaluation suite passes agreed thresholds.
- Observability exists for latency, errors, source failures, and QA failures.
- Known limitations are visible in the product and docs.

Minimum pilot thresholds:

- Zero known utility capacity overclaims.
- No final/report-ready material claim without source support or explicit assumption.
- Data gaps visible for missing, partial, unavailable, or ambiguous fields.
- SMEs can inspect traces and source bundles.
- Agent output can be corrected without losing source lineage.

## Gate 8: Production Readiness

Before production:

- Auth and project-level permissions are enforced.
- Artifact persistence is durable and backed up.
- Audit logs are retained.
- Evaluation suite runs on release candidates.
- Source coverage and geography limits are documented.
- Incident and rollback process exists.
- Cost/latency controls are in place.
- SME feedback loop is operational.

## Readiness Summary

The agent can start implementation before every future data connector is complete, but it
should not produce trusted work product until the BE data contract for the scoped MVP is
complete, validated, provenance-backed, and explicit about gaps.
