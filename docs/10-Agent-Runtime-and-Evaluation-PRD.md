# Civil1 Agent Runtime and Evaluation

Product requirements document - Draft v1 - September 7, 2026

**Status:** proposed; pending product, engineering, domain and privacy/security approval. No implementation, model deployment or customer-use approval is implied.
**Accountable owner:** product/founder; assign a named individual before acceptance.
**Delivery owners:** application/platform engineer and data/agent engineer. Domain reviewer owns semantic adjudication. The existing two-developer constraint remains; these are responsibilities, not additional hires.

Companions: [01 - Product scope](https://github.com/DataFaceLabs/civil-ai-data/blob/develop/docs/design/civil1-platform-design/01-PRD.md), [02 - Data contracts](https://github.com/DataFaceLabs/civil-ai-data/blob/develop/docs/design/civil1-platform-design/02-Technical-Spec.md), [03 - Questions and sources](https://github.com/DataFaceLabs/civil-ai-data/blob/develop/docs/design/civil1-platform-design/03-Coverage-and-Source-Plan.md), [04 - Task execution](https://github.com/DataFaceLabs/civil-ai-data/blob/develop/docs/design/civil1-platform-design/04-Implementation-Guide.md), [08 - Agent strategy](https://github.com/DataFaceLabs/civil-ai-data/blob/develop/docs/design/civil1-platform-design/08-LLM-and-Agent-Strategy.md), [09 - Trust Console](https://github.com/DataFaceLabs/civil-ai-fe/blob/develop/docs/09-Trust-Console-PRD.md), [11 - Production acceptance](https://github.com/DataFaceLabs/civil-ai/blob/main/docs/11-Production-Acceptance-and-Operations-PRD.md), [implementation order](https://github.com/DataFaceLabs/civil-ai/blob/main/docs/civil1-design-package-index.md#suggested-implementation-order).

Evidence: [September 7 implementation assessment](https://github.com/DataFaceLabs/civil-ai/blob/main/docs/research/agent-strategy-assessment-2026-09-07.md) and [production-design research](https://github.com/DataFaceLabs/civil-ai/blob/main/docs/research/agent-production-design-evidence-2026-09-07.md). External guidance informs safeguards; it does not establish Civil1 accuracy, installed SDK behavior or actual account permissions.

## 1. Product Decision

The Agent turns admitted, release-pinned evidence into a bounded investigation and a reviewable decision record. It explains what is supported, conditional, unknown or conflicting, and identifies the next useful verification action. It does not create regulatory authority, silently approve data or replace professional judgment.

The first product increment has three customer-facing workflows: answer a scoped question, produce a due-diligence gap-to-action brief, and QA a saved study. Internal ordinance extraction is a separate workflow with a stricter promotion/review boundary. Reuse deterministic section drafting and export for routine work; allow bounded tool selection only where investigation needs it.

**Success is a useful correct result, not merely a fluent response or a successful model call.** Measure unsupported conclusions, material omissions, correct supported answers, justified abstention, reviewer effort, latency and cost together.

## 2. Baseline and Scope

The September 7 assessment inspected Strands, registered tools, deterministic drafting, context, platform jobs, DSI and export paths. It found existing capabilities, not a blank application. It also reproduced an offline Topic Brief gate accepting an invented section/quote. It reported pinning, mutable run-context and recovery gaps at its inspected revisions. These are dated implementation anchors, not claims about today's deployment; AG-S0 must reconcile them.

Keep Strands, current provider adapters, existing pollable runs/artifacts, DSI, regulatory-text retrieval, section renderers, platform persistence and current FE surfaces. Do not build a parallel knowledge policy or semantics registry. AgentCore, Step Functions or another runtime may be evaluated only against the migration trigger in section 12.

### Included

- One named TX pilot scope and one named King scope using approved Q01-Q04 questions, intended use and domain-reviewed evidence.
- Typed release-pinned evidence tools, bounded regulatory retrieval and cross-section investigation over existing admitted sources.
- Claim-level support, conditions, citations, assumptions and explicit missing evidence in answers, briefs, QA and exports.
- Durable job control, per-run configuration, isolation, budgets, cancellation, evaluation and safe rollout.
- Internal SMC Title 23/KCC Title 21A extraction into existing DSI candidates, only where source rights and reviewers are available.

### Excluded or Deferred

- Autonomous source admission, production promotion, issue closure, permitting, external messages or changes to shared facts.
- New private-document ingestion, arbitrary shell/SQL, unrestricted internet agents or a general-purpose agent builder.
- Full feasibility certification, utility capacity inference, statewide completeness or a new jurisdiction taxonomy as a prerequisite.
- Multi-site/AOI comparisons beyond existing supported tools, customer MCP access, automated change alerts and long-term memory expansion. Each needs a separately accepted workflow.
- Provider/hosting migration, new vector infrastructure, multi-agent orchestration or fine-tuning without measured need and rights approval.

Existing authorized private inputs must be isolated and must not enter an unapproved provider route. This PRD does not authorize new categories of customer-data processing.

## 3. Users and Workflows

### AG-W1: Answer a Scoped Question

1. Resolve authenticated user/project, intended use, proposed use and parcel/jurisdiction context. Ask for missing decision-critical inputs or disambiguation.
2. Pin the study revision's evidence release and evaluate the question's prerequisites.
3. Retrieve only relevant facts, provisions and provenance; deterministic tools perform calculations and geometry work.
4. Return the supported answer with conditions, citations and missing dependencies. Do not treat a failed tool, missing source or unauthorized record as a negative fact.
5. Save the accepted output and actual configuration with the study revision. A request to use new evidence creates a new revision.

Success: the user can distinguish an answer from an assumption or unresolved question and inspect decisive evidence. A follow-up inherits the explicit study pin, not an unqualified current lookup.

### AG-W2: Due-Diligence Gap-to-Action Brief

1. Select a project, proposed use and bounded question set.
2. Assemble supported findings, material unknowns and conflicts across those questions.
3. Rank verified blockers and verification needs separately. Unknown must not mean favorable; uncertainty alone must not become a confirmed fatal constraint.
4. Return a compact brief containing finding, evidence/reason, affected scope, practical next action and responsible role or Unassigned. Do not invent an actual owner, deadline or agency requirement.
5. Preserve the structured result and render supporting prose/export through existing surfaces.

Success: a reviewer can explain what might stop the project, what remains unknown and what to verify next, without treating the brief as a complete feasibility assessment.

### AG-W3: Study QA

1. Load an authorized saved study revision and its actual supporting evidence.
2. Identify unsupported claims, inconsistent sections, missing conditions/citations and evidence changes relative to that revision.
3. Label suspected discrepancies as review findings with claim and evidence references. Distinguish a new-release change from an error in the old study.
4. Propose corrections without overwriting the original text. User acceptance creates an audited revision through existing controls.

Success: seeded material errors are found with supporting reasons and manageable false alarms. QA does not certify that uninspected claims are correct or silently fetch new evidence into old conclusions.

### AG-W4: Internal Extraction and Review

1. An authorized operator selects admitted source versions, jurisdiction/district, bounded controls and applicable use rights.
2. Retrieve complete relevant provisions, table headers, footnotes and necessary cross-references within the approved budget. Record omitted context; do not silently truncate away conditions.
3. Extract typed candidate controls with evidence locators, source/version, units, conditions and actual model/prompt configuration.
4. Apply deterministic support checks and domain review; reviewers correct, reject or accept individual entries. Reviewer changes retain original candidate and supporting evidence.
5. Only accepted entries enter the existing gated DSI/data release path. Rejected and unresolved entries remain non-definitive; source/rule changes invalidate affected reviews.

Success: review effort and accepted supported controls improve against the actual baseline. A successful batch or high sample score never promotes an unreviewed value.

## 4. Evidence and Answer Contract

These are logical obligations, not new transport field names or enums. Existing canonical models, DSI, knowledge/evidence policy, study artifacts and generated consumer contracts own the implementation. Data owns fact eligibility; platform owns study/run state and authorization; Agent owns bounded execution and validated output assembly; FE renders those contracts.

Each material factual claim must identify its evidence or an explicit limitation. Preserve entity/jurisdiction, intended use, release, dataset/rule/corpus versions, native source/record/section, relevant effective period, units, conditions, applicability and status. Derived calculations reference input facts and calculation version. Project assumptions are labeled inputs, not cited regulatory facts. Proposed actions and model hypotheses are separate from factual determinations.

Do not wrap an entire generated narrative in one unsupported claim. Apply the same eligibility policy to numeric fields, summaries, caveats, tables, follow-ups, QA findings and exports. A validated numeric field cannot legitimize an unvalidated narrative containing another decisive claim.

### Support Checks

| Layer | Required check | Failure behavior |
| --- | --- | --- |
| Structural | Schema, required fields, supported units/statuses; refusal and incomplete generation handled | Reject malformed output; bounded retry or explicit failure |
| Membership | Source/section belongs to the retrieved authorized version, not an invented identifier | Reject candidate/claim; never upgrade to complete |
| Quotation | Cited span exists under documented normalization; table context and cross-references retained | Missing/mismatched or incomplete support stays unresolved |
| Applicability | Correct jurisdiction, district, effective version, use, overlay and conditions | Suppress definitive interpretation or retain supported conditional result |
| Semantic support | Evidence entails the stated value/conclusion with its qualifiers | Domain review for regulatory extraction; evaluated claim-support policy for runtime answers |
| Eligibility | Approved fact/review state and allowed use; no candidate/inferred status stripping | Non-definitive evidence stays labeled and cannot silently enter the definitive path |

Schema-constrained output does not prove truth ([OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)). A second model may assist review but is not the sole promotion authority. Deterministic calculations and typed admitted facts remain preferred over asking a model to recompute them.

P0 extraction requires human review of **every entry proposed for definitive serving**, not only a sample. Review includes source support, applicability, conditions and units. The evaluation sample tests the workflow and throughput; it does not waive per-entry review. Existing inferred DSI entries must be reconciled with this eligibility rule and remain visibly non-definitive until accepted through the owning policy.

Memory, prior model responses and search snippets are not admitted facts. Revalidate factual context against the pinned evidence. Evidence restriction or revocation overrides convenient historical replay: retain only permissible audit metadata and show explicit unavailable/restricted evidence, never silently use current or leak a retained copy.

## 5. Runtime and Job Contract

Reuse existing run lifecycle and persistence. The stages below specify observable behavior, not a new enum or an instruction to adopt an orchestrator:

**Accept and persist -> acquire run ownership -> resolve evidence -> analyze -> validate -> persist artifact -> publish permitted result.** Slow retrieval and model calls occur after durable job acceptance, not in synchronous request preparation. Polling/reconnect must recover the same run and committed artifacts without resubmitting the job.

| Concern | Required behavior |
| --- | --- |
| Submission | Authenticate, authorize, validate scope, reserve bounded capacity/budget, persist request identity and acknowledge using the parent <2 s proposed p95 target |
| Idempotency | Key scoped to trusted tenant/project and normalized request; same key/same request returns original run, changed request conflicts |
| Ownership | Durable lease/conditional claim and fencing reject stale writers; at most one writer per conversation; independent conversations can proceed within global limits |
| Per-run state | No mutable shared search, scenario, credentials or provider/environment configuration across runs; instantiate or isolate clients/context appropriately |
| Checkpoints | Persist stage inputs/outputs and hashes; resume only with compatible data, policy, model and prompt versions; replay does not silently switch configuration |
| Duplicate delivery | Deduplicate committed artifacts and customer-visible effects; expired worker cannot publish after another takes ownership |
| Ambiguous provider result | Reconcile stored response/request identity before retry; model calls may have incurred cost even if response was lost; do not promise exactly-once provider billing |
| Retry | Only classified transient failures; bounded backoff/jitter honoring retry hints; authorization, invalid evidence and schema errors are not unlimited retries |
| Cancellation | Durably record cancellation, stop new work, fence late publication; already in-flight calls may finish or incur charges; no promise to recall/refund them |
| Budgets | Shared across stages, retries and resumes; reserve before external work, reconcile actual usage, fail closed when unbounded pricing/usage cannot be controlled |
| Failure | Terminal failed/cancelled/incomplete outcome retains permitted diagnostics; no success artifact from partial critical evidence |
| Recovery | Fault tests cover before/after model result, checkpoint write, lease expiry and final publication; completed results are not regenerated on reconnect |

Current [Strands session guidance](https://strandsagents.com/docs/user-guide/concepts/agents/session-management/) describes single-writer and persistence limits; inspect the installed version. [Lambda asynchronous delivery](https://docs.aws.amazon.com/lambda/latest/dg/invocation-async-error-handling.html) can duplicate even successful executions. A terminal-event check alone does not prevent overlapping in-flight attempts. If used, [Step Functions guarantees](https://docs.aws.amazon.com/step-functions/latest/dg/choosing-workflow-type.html) do not establish exactly-once downstream effects in the presence of retries or asynchronous delivery.

## 6. Security and Data Rights

### Trust Boundaries

| Boundary and asset | Threat | Required control and proof |
| --- | --- | --- |
| User -> run/study/artifact | Cross-tenant access or guessed session ID | Trusted identity, resource authorization on create/read/poll/cancel/export; denied calls return no protected payload |
| Model -> tools | Invented IDs, wider scope, privilege escalation | Server-side allowlisted typed tools and arguments; authorization independent of model/refusal |
| Retrieved text -> context | Indirect injection, false authority, poisoned memory | Untrusted-content handling, evidence eligibility and no tool authority from retrieved instructions |
| Retrieval -> network | Metadata/private-network access, redirect/DNS bypass | Approved source IDs/destinations; validate schemes/ports/resolved IPv4/IPv6, prevent DNS-to-connection bypass, controlled redirects and egress |
| Run -> provider | Unauthorized source/customer disclosure | Approved provider/model/endpoint/features/region and route-specific rights; minimize transmitted content |
| Run -> telemetry/eval/memory | Sensitive data retained outside intended boundary | Allowlisted metadata, protected diagnostic artifacts, retention/access/deletion policy and redaction tests |
| Model output -> rendered/exported result | Executable markup, unsafe links or unsupported conclusions | Validate structured data, safe rendering/link schemes and claim eligibility before publication |

P0 tools read evidence and compute bounded results. They cannot acquire production-write authority, publish data, contact third parties or edit source policy. Existing authenticated study-revision actions remain controlled by the user/platform, not a general write tool. Provider fallback may use only preapproved routes with equivalent rights and compatible evidence behavior; it must be observable and evaluated.

Follow [OWASP prompt-injection](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html) and [SSRF](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html) guidance. No prompt can replace authorization or network controls. Tests inspect actual attempted access and returned artifacts, not simply whether the model says it refused.

Provider no-training policies, `store=false`, and zero-data-retention eligibility are different. Record actual agreements/settings and endpoint exceptions before restricted content use. [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data) are specific to that provider; do not infer Bedrock or another provider's policy from them. Launch decisions and retention evidence belong to 11. This PRD approves no new external transmission.

## 7. Evaluation and Acceptance Policy

### Independent Evaluation Set

Proposed initial minimum: **60 independent task cases**, 20 each for AG-W1/W2/W3, balanced between the named TX and King pilot scopes, plus the AG-W4 extraction set of at least ten deliberately selected districts/parcels per pilot jurisdiction, extended for rule diversity. Build a scenario matrix covering supported answers, insufficient evidence, wrong authority, stale/contradictory evidence, conditions, retrieval truncation, fabricated citations, injection and cross-tenant attempts. Cases may exercise multiple dimensions; counts do not excuse a missing critical dimension.

Each customer workflow must include answerable and necessarily limited/unanswerable cases; QA has both seeded defects and clean controls. Reviewer labels identify expected material claims, necessary limitations and acceptable alternative actions. Group related parcels, districts and source documents to avoid development/holdout leakage. Keep held-out answers outside prompts, retrieval and memory. Quarantine any exposed holdout for development and replace it before release acceptance.

Run **three isolated trials per customer case** using the exact candidate configuration; retain every failure, timeout and cancellation in the relevant denominators. Publish first-attempt success and all-three-trials consistency, not just best-of-three. Repeated trials are correlated evidence, not three times as many independent geographic cases. Human reviewers calibrate automated graders against a blinded subset and all suspected severe defects; independently double-review at least 20% of cases and adjudicate disagreements before signoff.

Use the existing evaluation harness and trace tooling. Do not purchase or adopt a hosted eval platform merely to follow [OpenAI's evaluation method](https://developers.openai.com/api/docs/guides/evaluation-best-practices) or [Anthropic's agent-evaluation guidance](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents). Report sampling frame and uncertainty; this pilot does not support a population-wide accuracy or hallucination-free claim.

### Proposed Release Thresholds

These are Civil1 policy proposals, not vendor benchmarks. Product/domain owners must ratify them before release evaluation. Predeclare any changes before examining candidate holdout results; never relax a gate after a failure simply to ship. Severe failures cannot be averaged away by a passing aggregate.

| Metric | Definition and proposed gate |
| --- | --- |
| Severe unsupported conclusion | **Zero observed** across all required cases/trials: wrong authority, invented decisive control, unsupported negative constraint, omitted decision-changing condition, cross-release conclusion or restricted-data leakage |
| Structural evidence coverage | **100%** of material definitive claims have authorized resolvable evidence/calculation references; no narrative/export bypass |
| Semantic claim support | At least **98%** of evaluated material factual claims fully supported, with zero severe failures; report nonsevere errors and correct them before accepting the affected artifact |
| Useful answer coverage | At least **90%** of reviewer-labeled answerable W1/W2 cases produce a correct useful supported answer, not an unnecessary abstention |
| Justified limitation | At least **95%** of insufficient-evidence W1/W2 cases identify the necessary limitation and next evidence; no unsupported definitive answer is allowed by the remaining tolerance |
| Brief completeness | At least **95%** of reviewer-labeled material findings/unknowns included; **100%** of seeded decision-critical blockers/unknowns retained |
| QA usefulness | **100%** recall of seeded severe errors, at least **90%** recall of all labeled material errors and **90%** precision of raised material-error findings; clean controls included |
| Repeated-run consistency | At least **90%** of cases meet their complete task rubric in all three trials; report by workflow and jurisdiction as well as overall |
| Extraction promotion | **100%** of entries destined for definitive serving individually accepted by an authorized domain reviewer after support/applicability checks; zero known unsupported entries promoted |
| Review value | Compare actual baseline and candidate on the same cases: proposed **25% lower median reviewer task time** for W2/W3 without reducing correctness; measure extraction minutes per accepted control separately before promising throughput gains |

Also report incorrect answered / all answered, justified and unnecessary abstention, timeouts and incomplete evaluations. Zero denominators are not measurable, not a pass. Every workflow/jurisdiction stratum must meet its applicable gate; tiny strata require more cases where rates cannot support the decision. Compare against the current implementation and an always-abstain baseline. Human review of the pilot may catch an error but does not erase that pre-review model error from evaluation statistics.

P0 customer pilot outputs remain subject to human review before reliance or external delivery. Broad unattended rollout is not approved by a small holdout; it requires an explicit risk/monitoring decision using larger representative evidence under 11.

## 8. Performance and Cost Budgets

Proposed initial limits for the bounded pilot, subject to measured feasibility and pre-release approval:

| Work | Proposed p95 target | Hard total deadline | Proposed variable external-call spend ceiling |
| --- | --- | --- | --- |
| W1 scoped answer | 60 seconds | 180 seconds | USD 1 per run |
| W2 brief or W3 QA | 120 seconds | 300 seconds | USD 3 per run |
| W4 operator batch | Establish before scheduling from district/control count | Explicit approved batch deadline | Explicit batch ceiling; missing approval blocks batch execution |

These dollar amounts are ceilings, not predicted prices or total operating cost. Record model, token prices/version, provider usage, retrieval charges and unknown charges; an unknown-cost capability cannot run automatically outside an approved bounded envelope. Customer price and gross-margin decisions remain separate.

Proposed W1-W3 maxima per run: 8 model calls, 20 tool invocations, 64,000 total input tokens across calls, 8,000 total output tokens, 5 MiB retrieved text, and at most two retries per retryable operation. Every attempt consumes the same run budget; the most restrictive ceiling wins. Use stricter per-tool/provider limits where required. If a task needs more context, explicitly narrow it or request a separately approved run, never silently drop mandatory exceptions or reset budgets.

Measure queue delay, model/retrieval time, validation and rendering separately. Exercise five concurrent pilot runs for 15 minutes with isolated contexts, plus duplicate and cancellation scenarios. This is separate from the deterministic API capacity gate and is not 50-active-Agent readiness. Paid load/evaluation runs require an explicit aggregate spend and reviewer-hours cap under 11; reaching that cap yields incomplete evaluation, not success.

## 9. Functional Requirements

All requirements below are P0 for the accepted pilot except AG-23, which is a conditional infrastructure decision, not a migration requirement.

| ID | Requirement |
| --- | --- |
| AG-01 | Resolve authorized project/use/question context; preserve identity, ambiguity and decision-critical assumptions |
| AG-02 | Pin and propagate actual release/rule/corpus identity across every tool, follow-up, result and export |
| AG-03 | Validate material claim support through membership, quotation, applicability, semantics and eligibility; include summaries and prose |
| AG-04 | Preserve candidate/inferred/approved and unknown/conflicting/inapplicable distinctions through all consumers |
| AG-05 | Retrieve bounded complete relevant provisions and dependencies; expose missing/truncated conditions |
| AG-06 | Deliver W1/W2 structured findings, limitations and actionable next steps without fabricated commitments |
| AG-07 | Deliver W3 QA with claim-level evidence and non-destructive revision handling |
| AG-08 | Deliver W4 through existing DSI with per-entry review, audit and version-aware invalidation |
| AG-09 | Apply the same evidence policy to deterministic drafts, Agent narratives, Topic Briefs and exports |
| AG-10 | Authorize all run/artifact/tool operations in the control plane and validate tool scope independently of model output |
| AG-11 | Enforce retrieval/network/output defenses and no autonomous production-write authority |
| AG-12 | Enforce approved provider routes, data rights, redaction, scoped memory and retention |
| AG-13 | Use immutable per-run configuration and isolate mutable state across sessions/users |
| AG-14 | Persist acceptance/checkpoints and enforce distributed ownership, idempotency and stale-writer fencing |
| AG-15 | Bound retries, cancellation, deadlines and cumulative spend across resumes; no late publication |
| AG-16 | Preserve captured outputs and actual provenance; reconnect does not regenerate or substitute current evidence |
| AG-17 | Use independent held-out cases, repeated trials and calibrated human/automated grading |
| AG-18 | Meet approved safety, support, usefulness and review-value thresholds; failures/abstention remain in denominators |
| AG-19 | Meet approved per-run and aggregate performance/cost budgets with observed provider usage |
| AG-20 | Instrument actual configuration, stage/tool calls, outcomes and usage with privacy-aware correlation |
| AG-21 | Provide accessible run status, limitations, cancel/retry, evidence navigation and export using existing FE components |
| AG-22 | Roll out a compatible pinned configuration with kill switch, regression evidence and superseded-path removal |
| AG-23 | Evaluate a runtime alternative only when the existing implementation fails an accepted requirement after bounded repair |

## 10. Acceptance Scenarios

These are future implementation tests, not executed gates. Record a known-bad red run and corrected green run for each new blocking check. Assertions must read the actual tool call, stored artifact, access decision or serving response relevant to the defect.

| Test | Requirements | Observable acceptance |
| --- | --- | --- |
| AE-01 | AG-01, AG-02 | Ambiguous/cross-county ID and missing proposed use cannot become a guessed definitive answer; valid lookup preserves native identity |
| AE-02 | AG-02, AG-16 | Promotion between tool calls/follow-up keeps one release; historical unavailability is explicit; captured original output remains unchanged |
| AE-03 | AG-03, AG-09 | Invented section, invented quote and valid quote from wrong district fail in numeric fields, summaries, QA and exported prose |
| AE-04 | AG-03, AG-05 | Truncated footnote, table header, overlay condition or effective amendment cannot produce an unconditional control |
| AE-05 | AG-04, AG-08 | Inferred/candidate entry cannot be served as definitive; review correction preserves original and changed source invalidates affected approval |
| AE-06 | AG-06 | Supported answer succeeds; absent utility/constraint evidence remains unknown; brief distinguishes verified blocker from investigation need |
| AE-07 | AG-07 | QA detects seeded material inconsistency, leaves original revision intact and does not label all clean controls defective |
| AE-08 | AG-09, AG-21 | Existing deterministic report structure and required sections survive; export values/citations match accepted artifact; failed export does not alter study |
| AE-09 | AG-10, AG-12 | Another tenant's run/session/parcel artifact and revoked permissions deny actual reads/polls/cancel/export/tools without leaking evidence |
| AE-10 | AG-10, AG-11 | Injected source/memory instructions cannot widen tool permission, fetch metadata/private network via redirect/DNS, or execute markup/write operations |
| AE-11 | AG-12, AG-20 | Unapproved provider fallback is refused; secrets and restricted raw content absent from normal traces, URLs and evaluation exports |
| AE-12 | AG-13 | Concurrent runs with different model/guardrail/scenario settings retain their own actual configuration and results |
| AE-13 | AG-14, AG-16 | Duplicate in-flight delivery and expired lease yield one committed artifact; stale worker and conflicting idempotency payload cannot overwrite it |
| AE-14 | AG-14, AG-15 | Crash before/after checkpoint/provider response resumes safely, records uncertain charges and does not reset cumulative budget |
| AE-15 | AG-15, AG-21 | Cancellation during a model call prevents new work and late publication; reconnect exposes accurate state; retry is deliberate and authorized |
| AE-16 | AG-17, AG-18 | Empty/missing strata, exposed holdout, always-abstain candidate, biased judge and exhausted eval budget cannot pass release evaluation |
| AE-17 | AG-17, AG-18 | Versioned 60-case/three-trial customer suite plus extraction set reports all approved metrics, disagreements and failures with independent labels |
| AE-18 | AG-19, AG-20 | Authorized concurrency/budget exercise meets targets or blocks signoff; traces show actual tool calls/configuration and usage, not a fixed expected tool list |
| AE-19 | AG-21 | Keyboard/screen-reader user can inspect evidence, track a long job, cancel, reconnect and retry; status and error are not color-only |
| AE-20 | AG-22, AG-23 | Regressed configuration is disabled/rolled back without changing historical artifacts; any proposed runtime passes the same isolation/recovery/eval suite |

## 11. Observability and Customer Interaction

Operators must answer: which evidence/configuration produced this claim; why did the run fail or exceed budget; did another attempt publish; and which accepted studies used an affected configuration? Correlate run/attempt, stage, tool and authorized artifact references. Record actual model/prompt/guardrail/tool/runtime versions, timing, retries, usage and validation outcomes. Do not substitute a declared tool list for observed calls.

Use existing telemetry facilities; bounded metric labels for workflow/result/provider, not tenant IDs or full URLs. Logs/traces carry protected opaque identifiers when needed. No default raw prompts, private documents, secrets or hidden reasoning capture. Diagnostic/eval content requires scoped access and retention. Inspect SDK auto-instrumentation before exporting telemetry ([OpenTelemetry privacy guidance](https://opentelemetry.io/docs/security/handling-sensitive-data/)). Alert and exercise operator response under 11.

FE uses existing study/chat/job surfaces. Show a truthful bounded stage/status, not invented percent complete. Preserve supported partial evidence as explicitly incomplete when the critical run fails; no completed-report presentation. Keep evidence links, conditions and unknowns accessible. Show cancel requested versus cancelled honestly when calls remain in flight. Retry creates or resumes the explicitly identified operation under the original scope rules. Existing typography, native controls, keyboard focus and responsive conventions apply; no new dashboard or decorative chat experience is required.

## 12. Delivery and Open Decisions

| Stage | Existing task relationship | Exit evidence |
| --- | --- | --- |
| AG-S0 Reconcile baseline | IM-00, LLM-01/02 | Current Topic Brief/DSI/export/runtime paths, actual configuration, owners and reproduced defects; no new semantics registry |
| AG-S1 Enforce evidence boundary | LLM-03, IM-03 contracts | Negative citation/applicability cases fail closed, candidate policy enforced; safe restricted diagnostics may ship before full pinning |
| AG-S2 Pin and recover | IM-05/06, IM-08 job work | End-to-end release contract, isolated contexts, durable runs, budgets and cancellation accepted |
| AG-S3 Customer pilot | LLM-06; bounded W1-W3 tasks | Existing render/tool owners extended, independent holdout and human-reviewed pilot pass |
| AG-S4 Extraction pilot | LLM-04/05, WA-04 | Source rights, DSI eligibility and per-entry review established; accepted controls use existing data gates |
| AG-S5 Launch | Parent M4, production gates in 11 | Accepted metrics, operational exercise, compatibility, kill switch and actual serving verification |

AG-S4 may develop alongside AG-S2/3 once source/candidate contracts are stable; its definitive outputs cannot serve before data release and review gates. AG-S0/1 do not wait for a planner rewrite to fix an unsafe existing citation path.

Pending approval: named pilot questions/jurisdictions/use; rubric and numerical thresholds; domain-review capacity; provider rights/retention; paid evaluation budget; per-run ceilings; recovery and launch tier. Missing approval blocks the affected release claim, not drafting or independent offline fixes.

Retain existing hosting unless measured duration, concurrency, recovery effort or cost fails an accepted requirement after bounded repair. Compare a narrowly scoped alternative with identical evidence and failure tests; session isolation, memory and workflow persistence do not solve semantic correctness or application authorization. [AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-sessions.html) is optional and still requires application session-to-user mapping.

## 13. Definition of Done and Replacement

All accepted P0 requirements trace to an implementation task and observed acceptance evidence. Current canonical contracts and generated FE consumers agree. Known-bad fixtures have recorded red/green runs; holdout evaluation, reviewer approval, security and run-recovery exercises pass; actual deployed configuration and data artifacts match acceptance. No blanket production-grade or hallucination-free claim follows from this document.

Replace citation-presence-only acceptance with support checks; remove any narrative bypass, unpinned lookup, fixed fabricated trace list and migrated global mutable run state. Remove superseded code/tests in the owning change or record a necessary wrapper with owner and deletion date. Preserve useful deterministic drafting, DSI, existing tools, captured outputs and compatible legacy studies. No new engine is justified if it leaves the same old policy running beside it indefinitely.

Register accepted tasks in the existing tracker. This PRD adds the missing product/runtime acceptance contract, not a second execution roadmap. Follow the workspace archive policy when superseded or complete.