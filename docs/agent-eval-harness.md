# Agent Evaluation Harness — Design & Implementation

**Status:** design approved 2026-07-12, implementation staged. Owner: platform+agent.
Consolidates and supersedes the ad-hoc parts of `evaluation-strategy.md`; that doc remains
the higher-level dimension/gate blueprint, this is the concrete build.

---

## 1. Purpose

Today, tuning the agent is **manual**: define prompts → run → eyeball the output against a
client feasibility study → tweak → repeat. That loses history (was v3 better than v5 on
zoning?), can't catch regressions (a tweak that helps utilities but breaks flood), and
can't compare objectively.

The harness turns that loop into a **repeatable, versioned, measurable** system:

> Score the whole agent **config bundle** (every knob, not just prompts) against ground
> truth; attribute each gap to the right knob; track cost alongside quality; and keep a
> versioned ledger of every candidate and its scorecard.

**Cardinal rule it enforces:** *never fabricate.* Uncertainty is a first-class output, not
an error. The metric that matters most is **false-confidence rate → 0**.

**What it is NOT:**
- Not model *training* — that's the corpus flywheel (`agent-feedback-capture.md`), separate.
  **Evals measure; training improves.**
- Not export/formatting (the DOCX/template work).
- Not a replacement for unit tests (code correctness) — this is *behavioral quality*.
- Not manual SME review — though it *calibrates* against SME edits from the corpus.

---

## 2. What we evaluate — the knobs

The prompt is one of ~7 levers. Crucially, most live in a single versioned **config
bundle**, so one candidate captures them together:

| Category | Knobs | Where |
|---|---|---|
| Model & sampling | model preset (per-section), temperature, max tokens, response mode (structured/text) | config bundle |
| Prompts | system prompt, per-section templates, guardrail wording | config bundle |
| Data feed | `inputFieldCodes` per section (which fields the prompt receives) | config bundle |
| Retrieval | web search on/off, query mode, allowed/blocked domains, depth | config bundle |
| Guardrails | forbidden phrases, required disclaimers, enforcement | config bundle |
| **Data quality** | field coverage, `FieldStatus`, determinations, provenance | civil-ai-data (data layer) |
| Task structure | section decomposition, context/memory, tool orchestration | architecture |

**The eval's superpower is *attribution*.** A bad section score isn't self-explanatory —
the per-metric breakdown says *which knob* to turn: low `false_confidence` → prompt; thin/
empty section → data coverage; junk citations → web-search domains. Without this you tune
prompts when the real problem is missing data. The corpus reinforces it: an SME edit that
*adds a fact* signals a data gap; one that *rewords* signals a prompt gap.

---

## 3. Ground truth

- **Golden studies** — the 20 client feasibility reports + 3 demo studies. Reference for
  content, voice, and how real engineers handle gaps.
- **The corpus** (`civilai-agent-corpus-{env}`) — SME accept/edit/rewrite events. The
  living "what good looks like" signal; grows with every UAT interaction.
- **Anchor set (start here):** `509 Cresthill` (the only *infeasible* study — stresses
  gap/uncertainty handling) and `20401 Trappers Trail` (has live lake data *and* a golden
  report).

> **Caveat:** the corpus contains the SMEs' own recurring template-reuse *errors*. Evals
> target *correct* output, not blind "match the SME." Golden studies + determinations are
> the objective anchor; SME edits are directional signal.

---

## 4. Metrics (the scorecard)

Per **section**, per **study**, plus an aggregate.

**Uncertainty (the trust core):**
- `false_confidence` — asserts a fact as certain where `FieldStatus` is
  PARTIAL/AMBIGUOUS/UNAVAILABLE. **Target ≈ 0. The single trust-killer.**
- `appropriate_caveat` — a missing field is flagged *and* a verification step recommended.
- `status_preservation` — prose matches the field tri-state (no laundering
  UNAVAILABLE → confident claim).

**Grounding & traceability:** `unsupported_claim_rate`, `citation_coverage` (material
claims carry a source).

**Compliance:** `forbidden_phrase` (will-serve, guaranteed capacity…), `required_disclaimer`
(e.g. utilities "boundary only / confirm with provider").

**Fidelity:** `similarity`/`edit_distance` vs golden/SME-approved text; `section_completeness`.

**Cost:** tokens, `$`, latency per candidate — so quality-**per-dollar** is explicit and the
Haiku-4.5 choice is an evidenced decision, not a hunch.

---

## 5. Three scoring tiers

Per `agent-tuning-strategy.md`, most checks can be rule-based (cheap, deterministic, no
judge drift). Use the cheapest tier that can answer each metric:

1. **Rule** (deterministic) — forbidden phrases, citation presence, disclaimer presence,
   status preservation, false-confidence heuristics. No LLM, no cost, no drift.
2. **Judge** (LLM rubric) — style/voice match, caveat quality, section fit — the subjective
   dimensions. Anchored on explicit rubrics + periodic human calibration; prefer rule tier
   where a metric can be expressed deterministically.
3. **Determination** (grounded truth) — narrated conclusions checked against the
   determinations engine's known outcomes (feasible/infeasible, floodway, etc.).

---

## 6. The config ledger (version control + measurable quality)

The core of "version-control the prompts with scores attached" — generalized to the whole
config bundle.

- **Candidate** = a full config bundle (`{version, modelPreset, responseMode,
  sectionSystemPrompt, webSearch, sections:{prompt, inputFieldCodes, guardrails,
  searchHint}}`). A candidate can be "same prompts, temp 0.1" or "utilities gets 2 more
  input fields" — any knob.
- **Baseline** = a snapshot of James's *current* live config (`llm_defaults.py` / the
  tenant LLM-Lab config). Every change is measured against it.
- **Scorecard** = §4 metrics for that candidate (per-section, per-study, aggregate, cost).
- **Leaderboard** = all candidates ranked, with a **current/live** pointer and **per-section
  diffs** ("candidate-7 changed only utilities: `false_confidence` 0.14 → 0.02").
- **Storage** = git, for free version control + diffs + PR review:
  ```
  eval/experiments/{candidate_id}/
      config.json      # the full bundle
      scorecard.json   # metrics + cost, per section/study
  eval/leaderboard.jsonl   # append-only: {candidate_id, aggregate, key_metrics, ts, note}
  ```
  (Promote to S3 only if candidate volume ever demands it.)
- **Promotion** = when a candidate beats baseline on the gate metrics (and doesn't regress
  any section), it becomes the new `current`; update `llm_defaults.py` / the tenant config.

No new prompt-injection machinery: the platform already lets a config **override** the
baseline (that's how tenant LLM-Lab configs work). A candidate is just a config the runner
applies → runs → scores.

---

## 7. Architecture

```
 candidate config ──► RUNNER ──► agent output (per section, per study)
   (from ledger)        │  applies the config via the platform's existing
                        │  config-override; runs the live Layer-1 section-draft
                        │  path (/v1/tenant/llm/invoke) — not the dry-run scaffold
                        ▼
         field facts (status+provenance)  ◄── data API, by entity_id
                        │
                        ▼
        SCORERS  ── rule tier (deterministic)
                 ── judge tier (LLM rubric, calibrated)
                 ── determination tier (vs known outcomes)
                        │
                        ▼
        SCORECARD ──► LEDGER (git) ──► leaderboard + diff vs baseline
```

- **Lives in** `civil-ai-agent` (agent domain; extends the existing `eval/` package).
- **Consumes** the corpus (S3) for SME ground truth, the golden studies (structured
  benchmarks), and the data API (field statuses by `entity_id`).
- **Targets Layer 1** — the live `llm_defaults.py` / tenant-config section-draft path
  (`/v1/tenant/llm/invoke`), which produces the narration in the app today. The Strands
  agent (`civil_analyst.py`) is dry-run scaffolding; add it as a second target once it's
  the live path.

### One run, end to end
1. Pick a candidate config from the ledger.
2. For each anchor study: run each section with that config → narration.
3. Fetch field facts (with `FieldStatus`) by `entity_id`.
4. Score: rule tier (facts + prose), judge tier (vs golden/SME text), determination tier.
5. Emit the scorecard; append to the ledger; diff vs baseline.
6. Promote if it wins the gates without regressing a section.

---

## 8. Staged implementation

**Slice 1 — "the first real number"** (highest value, smallest surface):
- Rule-tier scorers for the uncertainty core (`false_confidence`, `appropriate_caveat`,
  `status_preservation`) + `forbidden_phrase` + `citation_coverage`.
- A runner over the 2 anchor studies against a candidate config.
- Snapshot James's current config as `baseline`; produce its scorecard = the number we
  improve from.

**Slice 2 — judge tier + the ledger:**
- LLM-judge scorer (style/caveat quality vs golden/SME text) with a rubric + calibration.
- Corpus edit-distance metric (score vs SME-approved text).
- The git ledger + leaderboard + per-section diffs + `current` pointer.

**Slice 3 — full harness + gates:**
- All sections; determination tier; cost tracking; regression view.
- Wire as a repeatable check (CI/nightly) with **release gates** (from
  `evaluation-strategy.md`): `false_confidence` ≈ 0, citation coverage on material claims,
  data-gap visibility, no section regression vs `current`.

---

## 9. Release gates (when it becomes a gate, not just a report)

Before a candidate is promoted to `current` / before a UAT-facing change:
- `false_confidence` ≈ 0 (no unsupported claims stated as fact).
- Material claims carry a source (`citation_coverage` threshold).
- Data gaps are visible (`appropriate_caveat` on UNAVAILABLE fields).
- No section regresses vs the current baseline.
- Cost within budget (quality-per-dollar acceptable).

---

## 10. Open items / decisions

- **Confirm Layer 1 as the initial target** (recommended — it's the live path).
- Structure the anchor golden studies (PDF → per-section benchmark files) — a one-time
  extraction; `509 Cresthill` + `20401 Trappers Trail` first.
- Judge model + rubric + calibration protocol (Slice 2).
- Where "promotion" writes back (edit `llm_defaults.py` vs the tenant baseline template).
