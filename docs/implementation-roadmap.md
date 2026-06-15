# Implementation Roadmap

## Purpose

This roadmap translates the Civil AI Agent design into delivery phases, epics, stories,
dependencies, and acceptance criteria.

The roadmap assumes the agent will launch only after the backend data contract is stable
enough for the selected MVP scope. The data lake does not need every eventual field, but
the MVP geography, section facts, source status, provenance, and project snapshot
behavior must be complete and validated for trustworthy agent output.

## Roadmap Principles

- Data trust comes before agent polish.
- The first agent should be read-only and inspectable.
- Durable artifacts come before autonomous actions.
- The workbench context envelope is a product contract, not an implementation detail.
- AgentCore, Strands, or another runtime should sit behind stable contracts.
- Every phase must improve evaluation coverage.

## Phase Overview

| Phase | Name | Outcome |
| --- | --- | --- |
| 0 | Prerequisites and readiness | BE/FE/eval contracts are ready for agent build. |
| 1 | Agent foundation | Contracts, scaffolding, tools, traces, and policies exist. |
| 2 | Read-only analyst agent | Agent can answer questions and create source-backed findings. |
| 3 | Drafting and QA | Agent can draft sections and flag unsupported or risky language. |
| 4 | Workbench artifact integration | Agent outputs can be saved, reviewed, revised, and exported. |
| 5 | Approved actions and expanded tools | Agent can recommend and prepare approval-gated actions. |
| 6 | Pilot hardening | Security, observability, evals, latency, and release controls are ready. |

## Phase 0: Prerequisites And Readiness

### Epic 0.1: Backend Data Lake MVP Readiness

**Goal:** Confirm the BE data platform is complete and validated for the agreed MVP
scope.

Stories:

- **AGENT-001: Define MVP geography and report scope**
  - Identify launch counties, jurisdictions, project types, and report sections.
  - Acceptance: scope document identifies included/excluded domains and known gaps.

- **AGENT-002: Validate section fact catalog**
  - Confirm the 11 BE section IDs, schemas, status values, and field names used by the
    agent.
  - Acceptance: `parcel-overview`, `zoning`, `flood`, `jurisdiction`, `watershed`,
    `soils`, `utilities`, `mobility`, `environmental`, `compliance`, and `provenance`
    contracts are documented with sample payloads.

- **AGENT-003: Validate service views and freshness metadata**
  - Confirm `svc_section_*` views are populated for MVP scope and expose freshness or
    snapshot metadata.
  - Acceptance: each MVP section returns expected status and source dates for test
    entities.

- **AGENT-004: Validate provenance contract**
  - Confirm every material fact can be traced to source records, derivations, uploaded
    documents, or explicit assumptions.
  - Acceptance: provenance payload supports source ID, source type, status, freshness,
    and citation/display metadata.

- **AGENT-005: Validate project snapshot/export behavior**
  - Confirm projects pin snapshot date and exports are reproducible.
  - Acceptance: same project export can be re-run and produces stable evidence for the
    same snapshot.

- **AGENT-006: Create BE coverage matrix**
  - Map each feasibility section to BE-backed, partial, missing, derivable, source-tool,
    and user-input fields.
  - Acceptance: matrix is reviewed by BE and agent stakeholders and linked from
    [Data Alignment](data-alignment.md).

- **AGENT-007: Establish data quality smoke tests**
  - Create representative entities and expected facts for MVP geographies.
  - Acceptance: smoke tests cover parcel, zoning, flood, jurisdiction, watershed, soils,
    utilities, provenance, and known partial cases.

### Epic 0.2: Frontend Workbench Contract Readiness

**Goal:** Align with FE on the context envelope and artifact lifecycle, even if the FE is
still POC.

Stories:

- **AGENT-008: Define workbench context envelope**
  - Specify project, entity, active section, selected artifacts, selected sources, map
    layers, proposed use, and user role.
  - Acceptance: FE and agent agree on the minimum context payload.

- **AGENT-009: Define agent response contract**
  - Specify message, artifacts, trace summary, suggested actions, and review state.
  - Acceptance: FE can render at least message, finding, data gap, risk, and draft
    section responses.

- **AGENT-010: Define artifact persistence ownership**
  - Decide where saved artifacts live before and after FE hardening.
  - Acceptance: owner is documented for findings, risks, draft sections, source bundles,
    exhibit references, and review states.

- **AGENT-011: Define review and approval states**
  - Align on draft, needs evidence, needs SME review, approved, rejected, and
    superseded.
  - Acceptance: review states are documented and role-gated states are identified.

### Epic 0.3: Evaluation Fixture Readiness

**Goal:** Make evaluation infrastructure available before the agent can produce polished
drafts.

Stories:

- **AGENT-012: Select golden feasibility studies**
  - Choose representative real reports across positive, constrained, and infeasible
    outcomes.
  - Acceptance: at least 10 cases are selected, including OSSF, floodplain, utility,
    ROW/access, Edwards, and jurisdiction ambiguity scenarios.

- **AGENT-013: Create source bundles**
  - Assemble BE facts, report text, template text, exhibits, source docs, and expected
    decisions for each case.
  - Acceptance: each golden case has an evaluation folder or structured fixture.

- **AGENT-014: Define automated checks**
  - Implement or specify checks for unsupported claims, missing citations, utility
    overclaims, status loss, and wrong feasibility posture.
  - Acceptance: checks are runnable against saved agent outputs.

## Phase 1: Agent Foundation

### Epic 1.1: Service And Runtime Skeleton

Stories:

- **AGENT-101: Choose initial runtime path**
  - Prototype AgentCore + Strands against contracts, or choose a smaller custom service
    if faster for MVP.
  - Acceptance: ADR records decision, tradeoffs, and fallback.

- **AGENT-102: Create agent API skeleton**
  - Expose an endpoint that accepts workbench context and user request.
  - Acceptance: endpoint returns structured response with trace ID.

- **AGENT-103: Implement trace envelope**
  - Capture request, context, tools, sources, artifacts, warnings, and response.
  - Acceptance: every agent run produces a trace summary.

### Epic 1.2: Tool Contract Foundation

Stories:

- **AGENT-104: Implement BE fact tools**
  - Wrap entity resolution, section facts, all facts, provenance, and project export.
  - Acceptance: tools return normalized facts, source refs, statuses, gaps, and errors.

- **AGENT-105: Implement policy gates**
  - Enforce no hallucinated facts, no capacity inference, and no mutating actions without
    approval.
  - Acceptance: tests prove blocked behavior for utility capacity overclaim and missing
    source claims.

- **AGENT-106: Implement artifact schemas**
  - Define finding, risk, data gap, draft section, source bundle, exhibit reference, and
    recommended action schemas.
  - Acceptance: schemas support source refs, status, assumptions, review state, and
    trace ID.

## Phase 2: Read-Only Analyst Agent

### Epic 2.1: Contextual Q&A

Stories:

- **AGENT-201: Answer project/entity questions**
  - Use current workbench context to answer without asking the user to restate parcel
    details.
  - Acceptance: answers cite facts and preserve partial/ambiguous/unavailable statuses.

- **AGENT-202: Explain source status and freshness**
  - Surface source status, snapshot date, and coverage limitations.
  - Acceptance: response distinguishes complete, partial, ambiguous, unavailable,
    not_applicable, and insufficient_data.

### Epic 2.2: Findings, Gaps, And Risks

Stories:

- **AGENT-203: Create source-backed findings**
  - Produce findings from BE facts and provenance.
  - Acceptance: each finding includes claims, source refs, status, and review state.

- **AGENT-204: Create data gaps**
  - Convert missing, partial, or unsupported fields into structured gaps.
  - Acceptance: each gap identifies type, section, recommended source/action, and
    blocking severity.

- **AGENT-205: Create initial risk items**
  - Flag known patterns such as OSSF, floodplain, utility capacity, ROW/access, and
    jurisdiction ambiguity.
  - Acceptance: risks include severity, evidence, caveat, and recommended follow-up.

## Phase 3: Drafting And QA

### Epic 3.1: Section Drafting

Stories:

- **AGENT-301: Draft priority sections**
  - Start with parcel overview, jurisdiction, zoning, watershed, flood, utilities, and
    summary.
  - Acceptance: drafts use ATX Civil voice and include source support, caveats, and
    required actions.

- **AGENT-302: Handle template deviations**
  - Expand, condense, mark not applicable, or reframe sections when evidence warrants.
  - Acceptance: deviation reason is captured in artifact metadata.

- **AGENT-303: Draft feasibility summary**
  - Generate feasible, feasible with conditions, constrained, infeasible as proposed, or
    insufficient data posture.
  - Acceptance: summary posture is supported by section risks and data status.

### Epic 3.2: Draft QA

Stories:

- **AGENT-304: Detect unsupported claims**
  - Parse draft claims and verify source support.
  - Acceptance: unsupported claims are flagged before save/export.

- **AGENT-305: Detect utility overclaims**
  - Ensure provider/service coverage is not drafted as capacity or will-serve.
  - Acceptance: QA blocks or warns on capacity language without provider evidence.

- **AGENT-306: Detect missing caveats**
  - Check whether partial/ambiguous/unavailable facts are caveated.
  - Acceptance: drafts with partial data include explicit caveats and next actions.

## Phase 4: Workbench Artifact Integration

### Epic 4.1: Save And Review Artifacts

Stories:

- **AGENT-401: Save findings and gaps**
  - Allow user to add findings and data gaps to the project.
  - Acceptance: saved artifacts retain trace, source refs, and review state.

- **AGENT-402: Save risks and recommendations**
  - Allow user to save risk items and recommended next actions.
  - Acceptance: saved risk links to sections, sources, severity, and owner/status.

- **AGENT-403: Save draft report sections**
  - Allow user to add draft language to report workspace.
  - Acceptance: draft section links claims to source refs and QA results.

### Epic 4.2: Review Workflow

Stories:

- **AGENT-404: Mark artifacts for SME review**
  - Support needs SME review state and reviewer comments.
  - Acceptance: review state changes are role-aware and auditable.

- **AGENT-405: Supersede stale artifacts**
  - Detect when snapshot/source changes make a saved artifact stale.
  - Acceptance: stale artifact can be marked superseded with replacement link.

- **AGENT-406: Export evidence packet**
  - Export source bundle, artifacts, and traces for review.
  - Acceptance: packet contains enough evidence for QA without chat replay.

## Phase 5: Approved Actions And Expanded Tools

### Epic 5.1: Permit And Action Planning

Stories:

- **AGENT-501: Create permit checklist**
  - Generate jurisdiction-aware required/likely approvals and dependencies.
  - Acceptance: each checklist item has source/rule support and confidence/status.

- **AGENT-502: Recommend operational actions**
  - Recommend utility provider confirmation, fire flow, survey, title, pre-app, TxDOT,
    TCEQ, and geotech/ERI actions.
  - Acceptance: actions are recommendations until approved.

- **AGENT-503: Add approval-gated action execution**
  - Prepare but do not execute external actions without explicit approval.
  - Acceptance: approval event is logged before any mutation or external send.

### Epic 5.2: Source Tool Expansion

Stories:

- **AGENT-504: Add document/source retrieval**
  - Search uploaded documents, template, manuals, and source bundles.
  - Acceptance: retrieved snippets are source-linked and bounded to project permissions.

- **AGENT-505: Add rule derivation tools**
  - Evaluate IC, OSSF, WQ/detention, flood study, and permit rules.
  - Acceptance: derivations return inputs, rule, citation, result, and confidence.

## Phase 6: Pilot Hardening

### Epic 6.1: Security, Observability, And Operations

Stories:

- **AGENT-601: Add auth and role enforcement**
  - Enforce user/project permissions for reads, saves, reviews, and actions.
  - Acceptance: role tests cover analyst, SME, reviewer, and admin behaviors.

- **AGENT-602: Add observability**
  - Track latency, tool errors, source failures, token/cost usage, approval events, and
    QA failure rates.
  - Acceptance: pilot dashboard or logs support operational review.

- **AGENT-603: Add release gates**
  - Require eval pass, smoke tests, and data readiness check before deployment.
  - Acceptance: release checklist blocks pilot if critical checks fail.

### Epic 6.2: Evaluation And Continuous Improvement

Stories:

- **AGENT-604: Run regression suite**
  - Execute golden cases against every release candidate.
  - Acceptance: unsupported claim rate, citation coverage, and blocker identification
    are reported.

- **AGENT-605: SME feedback loop**
  - Convert reviewer corrections into playbook, prompt, policy, tool, or BE data
    improvements.
  - Acceptance: feedback is triaged and linked to backlog items.

- **AGENT-606: Pilot readiness review**
  - Review security, data coverage, FE integration, eval results, and unresolved risks.
  - Acceptance: go/no-go decision is documented.

## Cross-Team Dependencies

| Dependency | Owner | Blocks |
| --- | --- | --- |
| MVP BE data coverage and validation | BE | Phases 2-4 |
| Provenance and status contract | BE | All report-ready claims |
| Project snapshot/export behavior | BE | Source bundles, QA, exports |
| Workbench context envelope | FE + Agent | All contextual agent calls |
| Artifact persistence | FE/BE/Agent decision | Phase 4 |
| Uploaded document/source access | FE/BE/Agent decision | Phase 5 |
| Auth/roles | FE/Platform/Agent | Pilot hardening |
| Golden evaluation fixtures | Agent + SMEs | Phases 3-6 |

## MVP Recommendation

The first usable MVP should include:

- Read-only project/entity Q&A.
- BE fact/provenance tools.
- Source-backed findings.
- Data gap generation.
- Initial risk detection.
- Drafting for a small set of high-value sections.
- QA for unsupported claims and utility capacity overclaims.
- Manual save or copy into the workbench, if durable persistence is not ready.

Avoid in MVP:

- External action execution.
- Fully automated final report generation.
- Broad live web/source crawling.
- Claims from model memory.
- Complex multi-agent UI.
