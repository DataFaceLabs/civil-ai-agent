# Civil Analyst Agent — Tuning & Disruptor Strategy

*Authored 2026-07-04. Synthesizes the vision docs (`agent-design.md`,
`evaluation-strategy.md`), the Fable 5 audit (`fable5-audit-findings/02-civil-ai-agent.md`,
grade C), the Fable 5 design mechanics (`fable5-design-findings/03-golden-eval-mechanics.md`,
`04-agent-memory.md`, `07-industry-benchmark.md`), and the corpus-validated
`feasibility-playbook/`. **Current-state claims are verified against `civil-ai-agent`
`develop` as of this date, not the 07-02 audit** — several audit findings remain live;
a few infra items (CI, dev HTTP wrapper, `ZONING_DISTRICT` fix) have since shipped.*

This is the connective document the repo was missing: the vision doc says *what to build*,
the eval doc says *what to measure*, the Fable design docs say *how the mechanics work* —
this says **what to do, in what order, and why**, as an executable tuning roadmap.

---

## 1. What the agent is — and is not

### Identity

The **Civil Analyst** is a per-section *investigative drafting* agent for land-development
feasibility studies in the Austin metro. Its one job: take a parcel + a report section,
**investigate** it against governed data, **draft** the section in ATX-Civil house style,
**cite** every claim, and **flag every gap** — so a P.E. *verifies* rather than *authors*.

### The load-bearing design decision (the moat)

**The LLM never makes the regulatory determination.** Feasibility calls come from the
deterministic rule engine (`/v1/entities/{id}/determinations` — an *(applicability,
ordered rules, conclusion)* triple with a class taxonomy, confidence enum, and regulatory
citation). The agent investigates, drafts, explains, and cites — it does not decide. This
is the single most defensible thing in the platform and it maps 1:1 to what a P.E. must
defend. Every comparator that emits "feasibility" does it as a black-box score; none
exposes machine-readable rule provenance. **Do not erode this line.**

### Why this works (the playbook proof)

The `feasibility-playbook/` blind-holdout study settles the product thesis empirically:
**89% of feasibility-study content was PARTIAL-or-better and 73% EXACT/STRUCTURAL** —
playbooks written from 16 studies predicted the branch, skeleton, and often verbatim
prose of 4 never-read studies. Feasibility authoring is **jurisdiction-keyed template
assembly with slot substitution**, not free composition. The agent's job is *grounded
assembly + honest gap-flagging*; the SME's job is *verify, not write*. That makes the
agent a force multiplier on a task that is provably ~89% mechanical — the boundary being
jurisdiction edges and the free-form 4.0 Summary, where it stays draft-with-SME-review.

### What it should do

- **Per section**: resolve parcel → pull governed facts + run determinations + provenance
  → draft to the corpus pattern → attach a citation to every regulatory value → surface
  `status: partial/unknown` fields as explicit verification steps.
- **Assemble the proven-mechanical parts**: the CAD block (§2.3, 4/4 EXACT in holdout),
  the FEMA master stem (4/4 EXACT), the exhibits list (mechanically derivable from
  "(See Exhibit N)" callouts in first-citation order), the permit assembler (which
  *extrapolated correctly to a jurisdiction never seen in training*).
- **Sell the gaps.** Data gaps rendered as a verification checklist are a *feature* —
  competitors hide gaps; honest-gap semantics end-to-end is a differentiator.

### What it must NOT do (guardrails as testable behaviors)

- **Not make the regulatory call** — the rule engine does.
- **Not infer capacity from coverage.** The sharpest guardrail in the suite. Howard Ln
  is the canonical trap: CoA territory says "served," but the nearest wastewater main is
  ±1,137 ft → OSSF. Any draft that says "wastewater is available" here has failed.
- **Not fabricate.** No fact without a governed source or a web result actually returned
  this run; no citation to a page it was never shown.
- **Not reproduce the SME's known errors.** The corpus contains recurring template-reuse
  mistakes — SSURGO soils mislabeled "USGS," HSG D called "well-drained," an Elgin
  (Bastrop) parcel's FIRM cited as "Travis County," the IFC edition self-contradiction.
  Generate from the lake; emulate the *structure*, not the errors.
- **Not emit third-party PII.** Named staff, direct lines, personal emails on the
  studies' contact pages → role-based departmental contacts only.
- **Not present "feasible" while a `fatal` blocker is open.** Posture must reconcile with
  open critical sections.
- **Not be a P.E., a will-serve source, or a legal engine** (the explicit non-purpose
  list in `agent-design.md`).

---

## 2. Does it have the proper tools?

**The tool *inventory* is right; the tool *wiring* is broken and the tool *contract* is
too thin.** Six tools, mapping cleanly to the investigation loop:

| Tool | Role | State (verified on `develop`) |
|---|---|---|
| `resolve_parcel` | address/prop_id → entity_id | 🔴 **F1 bug live** — sends `{"prop_id": …}`; backend `EntityResolveRequest` is `extra="forbid"` and accepts only `parcel_id`. Every prop_id lookup **422s**. Address path works. |
| `get_section_facts` | governed facts for one section | ✅ works |
| `get_site_payload` | full FE-shaped site payload | 🔴 **F1 bug live** — calls `GET /v1/fe/site?entity_id=…`, a route that does not exist. Backend now has `GET /v1/fe/site/by-entity/{entity_id}` (PII-scoped). One-line fix. |
| `get_provenance` | source records for facts | ✅ works |
| `run_determinations` | invoke the rule engine | ✅ works — **this is the tool that keeps the regulatory call out of the LLM.** |
| `web_search_deduped` | fill gaps not in the lake | ⚠ works, but `dedupe_hit` flag is wrong (F6) and session state is a global singleton (F8). |

**Three tool-layer problems to fix:**

1. **Two core tools fail against the real backend (F1).** Small, documented fixes:
   `prop_id`→`parcel_id`, and repoint `get_site_by_entity` to the new by-entity GET.
2. **No structured error shape.** The HTTP chain is a bare `raise_for_status()`, so a
   422/404 surfaces as a raw `httpx` exception out of the tool, not a
   `{status, data, sources, errors}` result the model can *recover* from. This violates
   the repo's own `tooling-and-orchestration.md` and Anthropic's "writing tools for
   agents" guidance (errors should be informative, recoverable results). Give every tool
   a typed envelope.
3. **Missing tools for the target state:**
   - **Catalog/enum discovery.** The data platform *has* a catalog API (domains, sections,
     fields). The agent should query it for enum discoverability rather than guessing
     field vocabularies (closes the D10 self-description gap on the consumer side).
   - **Records/document retrieval** (long horizon). Feasibility is *half records-shaped*
     (plats, deeds, easements, dev agreements, title commitments) and the studies show
     these are **dispositive, not supplementary** (Kenny Fort's use is set by a condo
     declaration *overriding* PUD zoning). This is the hardest gap and a potential
     second moat — but it depends on the data-side records tier (D9), so it is a
     dependency, not a near-term agent task.

---

## 3. Where we are today

### Good

- **The architecture is best-in-field.** The determination division of labor is the moat;
  the 6-tool loop is the right shape; `run_determinations` correctly wires the agent to
  the rule engine.
- **It's reachable for evaluation now.** The dev HTTP wrapper (`civilai-agent serve`,
  shipped this session) means we can actually drive it — the precondition for any tuning.
- **CI + `make gauntlet` exist now** (shipped this session).
- **The blueprints are written.** `evaluation-strategy.md` is the eval *spec*; Fable
  design 03 is the eval *mechanics*; Fable design 04 is the memory *mechanics*. We are
  not designing from scratch — we are executing written designs.
- **Data coverage is healthier than the audit assumed.** The 2026-07-04 gauge shows the
  determination engine spans all 10 sections and coverage is substantially green in the
  **core counties (Travis/Williamson/Hays)**, including the appraisal roll and Edwards.
  Grounding has real data to ground against in the core geography.

### Bad (all verified live on `develop`, not inherited from a stale report)

| # | Problem | Consequence |
|---|---|---|
| **F2** | Structured-output path **never driven on the live path** — `runner.py:48` calls `finalize_text_output(text=…)` with no `structured_mode`, so `structured` is always `None`. | **`AgentResponse.artifacts` is always empty in production.** The artifact-lifecycle product principle is unimplemented end-to-end, *and* the eval's rule checks have nothing structured to check. **This is the keystone bug.** |
| **F1** | Two contract bugs (above). | Core tools 422/404 against the real backend. |
| **F3** | The `enforce=False` guardrail's required disclaimer is **unconditional** — every output must contain the verbatim utility-coverage sentence. | The flag is *unflippable*: turning it on hard-fails every non-utility run ("what county is this?"). |
| **F5** | `TraceSummary.tools_used` is a hardcoded 5-tuple, reported on every run. | The trace **lies** — for a product whose stated differentiator is "inspectability is a feature," a fabricated trace is worse than none. |
| **F6** | `dedupe_hit` uses a cumulative session counter. | The model is told fresh queries are duplicates → won't rephrase/retry. Cross-run contamination via a module-global 300s cache. |
| **F8** | `_session`/`_client` are module-global singletons; the platform imports the agent in-process. | Concurrent runs cross-contaminate state — latent defect for the documented multi-user topology. |
| **F9** | Zero cross-turn memory; every run builds a fresh `Agent`. | "Make it shorter" and QA-review mode (capability mode 4) are impossible. |
| **F10** | Eval harness checks exactly two budget ceilings. | **Tuning has no quality signal.** This is the largest plan/practice gap. |
| — | Default model is **Haiku 4.5**; no prompt caching; system prompt is a thin 12-line rules block. | Cost/latency left on the table; drafting quality + guardrail adherence may be under-served by the smallest model on the hardest turn (see §6). |

**One-line diagnosis:** three repos each hold a real piece (facts+determinations; agent
scaffold; auth/control plane) and the execution gap is almost entirely *assembly* — plus
one keystone (F2) that gates both the product and the eval.

---

## 4. The path to a "disruptor" agent

### What makes it a disruptor (lean into the moat)

The benchmark verdict: **nobody in the field has** governed determinations + provenance +
honest gaps + jurisdictional depth. Regrid solved parcels; Harvey/Hebbia solved
document-copilot UX; TestFit/Deepblocks solved massing — **none produces a defensible
regulatory narrative study grounded in a rule engine.** The disruptor is the agent that
turns our moat into a deliverable the customer cannot reproduce elsewhere:

1. **Every sentence pinned to a fact / determination / document citation** — Harvey-grade
   UX, but grounded in a rule engine nobody else has.
2. **Gaps sold as verification checklists** — the honest-gap semantics competitors hide.
3. **Jurisdiction-keyed assembly** — the playbook's proven 89%, extended to the suburban
   manual tier (LCRA HLWO, Pflugerville EDM, San Marcos) the catalog doesn't yet cover.
4. **Exhibit assembly** — deliverable-parity: the studies carry 14–23 exhibits each and
   cite them constantly; this is the feature that makes the output an actual study.

### Sequenced roadmap (dependency-ordered — each phase unlocks the next)

**Phase 0 — Unblock the backend (days).** Fix F1 (both contract bugs) + give tools a
structured `{status, data, sources, errors}` envelope. *Without this the agent cannot
touch the real backend, so nothing downstream can be measured.* Add body-matching to the
tool tests so a contract regression fails CI (the current mock-shaped tests pass over the
live 422 — audit F4).

**Phase 1 — The keystone: drive structured output in production (F2) (days).** Make the
live path parse `SectionDraftOutput` so `draft_section` artifacts materialize. This single
change unlocks **both** the product (artifacts, claim→source pinning) **and** the eval
(6 of 9 strategy-doc checks become rule-based instead of judge-based). *Highest-leverage
change in the entire program. Do it first after Phase 0.*

**Phase 2 — Build the eval harness (1–2 weeks).** Per Fable design 03: golden cases as
structured artifacts, three tiers (rule/judge/determination). Start with **509 Cresthill**
(the corpus's only infeasible; tests infeasibility detection) — build the four rule checks
(placeholders, overclaims, citations, posture), wire pytest Tier R. **2121 Howard Ln is
parked**, not a starting case: confirmed a 3-parcel assemblage (`civil-ai` ADR-0004) — the
single sub-parcel the platform can resolve today gives a factually wrong `ossf_required`
against the real combined-site study, so it can't yet serve as the coverage≠capacity golden
case without either the assemblage gap addressed or a different single-parcel case standing
in. *Building this suite is what turns "tuning" from vibes into measurement.* (See §5.)

**Phase 2.5 — Port the validated playbook in, before any model A/B (days–1 week).**
*Execution detail: `docs/playbook-integration-plan.md` — the sequenced, one-rule-per-PR
backlog with per-rule acceptance cases and the deterministic-before-prose ordering.*
`feasibility-playbook/` (89% PARTIAL-or-better across 120 blind-scored holdout cells — a
fourth Fable 5 pass, same rigor as the audit/design/bughunt) has **zero footprint in
production** — confirmed via code search, zero references anywhere in `civilai_agent/src/`.
Two separable halves, in this order:
1. **Deterministic corrections into `civil-ai-data`'s determination YAMLs.** The playbook's
   own "Amendments required" list is already validated and ready to build: the OSSF
   lot-size gate (<1.0 ac infeasible / 1.0–1.5 ac advanced treatment / ≥1.5 ac conventional,
   with an "existing OSSF retained" exception — today's `wastewater_service` rule only gates
   on the `ossf_required` boolean, no lot-size logic at all), the §212.004 plat-exemption
   gate correction, floodplain-study dispatch keyed on proposed work-scope (not FEMA zone),
   and the TIA-trigger over-firing fix in CoA. Zero model-dependency, lowest risk, ready now.
2. **Jurisdiction-keyed drafting guidance into the structured-draft prompt** — boilerplate
   stems and branch-selection logic per section. Sequenced *after* the YAML corrections so
   the model drafts against corrected determinations, not stale ones.

Do the Haiku/Sonnet/Nova/Kimi model comparison only *after* this lands, not before —
comparing models on a task that doesn't yet have the domain's validated patterns loaded
tests the wrong thing. (All four confirmed live on Bedrock via direct catalog query, zero
new provider code needed; true GPT-4.x/5.x is not on Bedrock — only OpenAI's open-weight
`gpt-oss` family is — and would need a new provider adapter.)

**Phase 3 — Make guardrails real (days).** ~~Make the disclaimer *conditional on utility
content* so `enforce=True` is flippable (F3)~~ **done** — disclaimer now scoped to
`disclaimer_sections` (utilities today), and the `will-serve` forbidden-phrase check is
sentence-level context-aware instead of a blind substring match (was flagging safe usage
like "obtain a will-serve letter" identically to a real overclaim). Live-verified via the
eval harness: a soils draft went from 1 false-positive warning to 0.
Remaining: fix `dedupe_hit` (F6); fix the trace (F5); thread session state per-run instead
of globals (F8, also blocks safe bake-off parallelism — see `SMOKETEST-TRACKER.md`).

**Phase 4 — Memory (1–2 weeks).** Per Fable design 04: S3 session manager for short-term
("make it shorter" works), then `DraftRevision` + `AnalystCorrection` in the platform
single table for long-term. Unlocks multi-day studies, QA-review mode, and "the draft, not
the transcript, is the durable anchor." Mostly platform work; the agent change is a
`session_id` field + `PriorSectionState` injection.

**Phase 5 — Differentiators & efficiency (ongoing).** Prompt caching (the system prompt +
near-identical fact payloads re-send every run — first-line guidance for this workload);
the catalog/enum tool; exhibit assembly (deliverable-parity); records-tier tool (long
horizon, gated on data-side D9).

---

## 5. How we evaluate it for iterative tuning

**This is the heart of "tuning": you cannot tune what you cannot measure, and the eval is
the highest-leverage investment.** The full mechanics are in Fable design 03; the operating
model:

### Golden cases

Structured artifacts (`evals/cases/<id>/case.yaml`) authored from real client PDFs: atomic
**facts** (typed value + verbatim quote + page anchor + `status` + `source_class` +
`backend_coverage`), **blockers**, **required_actions**, and per-section **expectations**
(`must_state`, `must_not_state`, `must_cite`, `must_flag_unknown`). PII-scrubbed; the raw
PDF never enters the repo (referenced by filename + SHA256). Quote-substring validation at
authoring time makes a hallucinated fact structurally impossible to commit.

### Three tiers — never blended into one number

- **Tier R (rule, gating, in CI).** Deterministic checks: unresolved placeholders, capacity
  overclaims (lexicon + value-leakage on `unknown` fields), regulatory-value↔citation
  co-occurrence, posture vs. golden posture + open `fatal` blockers, source-ref vocabulary
  resolution, `must_flag_unknown` coverage. **Failures block a PR.** *Depends on Phase 1 —
  without structured output these degrade to slow, costly judge checks.*
- **Tier J (grounding judge, tracked).** Closed-book LLM judge decomposes the draft into
  atomic claims and labels each `supported | contradicted | unverifiable` **against only
  the case fact sheet** (forbidden from using world knowledge). Flagship metric:
  `unsupported_claim_rate = (contradicted + unverifiable) / total_claims`, with
  `contradicted` reported separately (far worse). Ships behind a calibration gate
  (Cohen's κ ≥ 0.8 vs. two-engineer adjudicated labels + a canary set + zero
  false-`supported` on `contradicted` items). **Grounding needs no SME** — the fact sheet
  is the authority.
- **Tier D (determination accuracy, quarantined).** Posture match + blocker-identification
  against case truth. Computed and reported from day one but **excluded from release gates**
  until an SME validates each case (`sme_validated: true`). This keeps the open SME
  ground-truth blocker *visible in the numbers* instead of designed around.

### The tuning loop

```
change (prompt / tool / model / temperature)
  → run golden suite
  → Tier R must stay green            (hard gate — regression blocks)
  → Tier J unsupported_claim_rate must not regress; contradicted_count must stay 0
  → inspect per-claim diffs on the two richest cases
  → keep the change iff it improves Tier J without breaking Tier R
```

### Metrics to track per iteration

| Metric | Tier | Target |
|---|---|---|
| Capacity-overclaim violations | R | **0** (release gate) |
| Unresolved placeholders / fabricated values on `unknown` fields | R | **0** |
| Citation coverage (regulatory values with a rule cite) | R | trend ↑ |
| `unsupported_claim_rate` | J | trend ↓ (flagship) |
| `contradicted_claim_count` | J | **0** (over-crediting fabrication is unacceptable) |
| Blocker-identification recall | R+J | trend ↑ |
| Posture match | D (quarantined) | reported, not gated, until SME |

### The critical dependency, stated plainly

**Structured output (Phase 1) and the eval (Phase 2) are the same critical path.** Six of
nine checks are rule-based *only if the structured path runs*. So the eval runner drives
the structured path explicitly (`finalize_text_output(..., structured_mode=True)`) rather
than waiting on the production wiring — but fixing production wiring (F2) removes that
workaround and makes production and eval identical. Prioritize F2 accordingly.

---

## 6. Staff+ judgment: sequencing, model choice, and risks

- **Do not tune the prompt or model before the eval exists.** You would be flying blind —
  the exact trap the audit names ("evals are the highest-leverage investment"). Phase 2
  precedes any prompt/model experimentation. The *first* legitimate tuning experiment is
  "does the eval move when I change X," and X needs a scoreboard.

- **Model choice is itself a tuning lever, and the current default is worth revisiting.**
  The agent runs on **Haiku 4.5**. That is a defensible cost choice for the *tool-orchestration*
  turns (resolve → facts → determinations), but the *grounded-drafting turn* — where
  guardrail adherence (never overclaim), structured-output fidelity, and citation
  discipline matter most — is where the smallest model is most likely to cost you Tier J
  points. Once the eval exists, run the A/B: Haiku throughout vs. Haiku for tool loops +
  a stronger Claude model for the final structured draft. Let the `unsupported_claim_rate`
  decide, not intuition. (Default to the strongest models for the drafting turn until the
  eval proves a cheaper one holds the line.)

- **Coverage bounds grounding — pick UAT/eval cases deliberately.** The agent can only
  ground what the lake serves. Core counties (Travis/Williamson/Hays) are green; Bastrop/
  Caldwell and mobility are thin. For measuring *agent capability*, weight cases toward the
  green geography so you are testing the agent, not the data gaps. But **include 2–3
  out-of-coverage cases** (Burnet, Hays edges) because *surfacing data gaps is a
  first-class product behavior* — the agent should score well by flagging, not fabricating.

- **The SME ground-truth blocker is real but narrow.** It blocks determination-*accuracy*
  labels (Tier D), not *grounding* labels (Tier J). Grounding is closed-book against the
  fact sheet and any careful engineer can label it. **Do not wait for the SME to start
  tuning** — Tiers R and J run today.

- **Concurrency and trace integrity are prerequisites for the sold product, not polish.**
  F8 (global singletons) corrupts multi-user runs; F5 (fabricated trace) undermines
  "inspectability is a feature." Both are cheap and both gate credibility.

- **KISS/YAGNI holds.** No eval framework, no dashboard until there are numbers worth
  dashboarding; checks as plain functions; one case format; two counterfactual variants
  max; no OCR/table extraction (a human transcribes 20 image-tables in minutes); no
  semantic/vector memory until active corrections outgrow a prompt injection.

---

## The one-paragraph version

The agent is a per-section investigative drafting assistant whose defensibility rests on
*not* making the regulatory call — the rule engine does. The plan is best-in-field; the
implementation is a thin prototype with one keystone bug (structured output never runs, so
artifacts are always empty and the eval has nothing to check) sitting on top of two live
contract bugs. The path is: unblock the backend (Phase 0), turn on structured output
(Phase 1 — the keystone for both product and eval), build the golden-eval suite starting
from the two richest real cases (Phase 2 — the tuning scoreboard), make the guardrails
actually enforceable (Phase 3), add memory (Phase 4), then lean on the moat with pinned
citations, honest-gap checklists, and exhibit assembly (Phase 5). Tune against
`unsupported_claim_rate` with a zero-tolerance on contradicted claims and capacity
overclaims — and don't touch the prompt or model until that scoreboard exists.
