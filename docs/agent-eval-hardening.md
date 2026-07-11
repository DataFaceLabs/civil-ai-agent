# Agent eval hardening (feature/agent-eval-hardening)

**Scope:** Section draft accuracy and transparency on James's Strands path.  
**Out of scope:** `assistant_chat`, platform search envelope, FE chat rail.

## Goal

Python decides branch and blocks when data is missing; Haiku renders prose only for
zoning, environmental, flood, and utilities. No confident narration on null or pending
governed facts.

## Toggle

```bash
export CIVILAI_AGENT_HARDENING=1
# Mutually exclusive with full pipeline for section_draft:
unset CIVILAI_DRAFT_PIPELINE
```

Priority in `run_agent()`:

1. `CIVILAI_DRAFT_PIPELINE=1` → full pipeline (all four sections)
2. `CIVILAI_AGENT_HARDENING=1` → hardening (H1–H4 below)
3. default → Strands tool loop

## H1 — Gates (all sections)

| Gate | When | Behavior |
|------|------|----------|
| `missing_entity_gate` | No `entity_id` | Blocked artifact, no LLM |
| `zero_fact_gate` | Empty section facts | Blocked artifact, no LLM |

## H2 — Dispatch + render (all default sections)

Reuse pipeline `dispatch_*` + template/render for **zoning, environmental, flood,
utilities** (eval-harness `DEFAULT_SECTIONS`). Other section IDs still fall back to
Strands legacy.

## H3 — Block-not-guess (zoning)

`zoning.county_no_zoning` only when `county_non_zoning_confirmed` flag is set.
Null `zoning_code` on county track → `zoning.pending` (no “Travis is non-zoning”).

## Eval regression

Baseline (live loop): `uat-baseline-live-agent-full20-haiku-20260709` — 61/68 (90%), 7 MISS.

Re-run with hardening:

```bash
cd eval-harness
set -a && source ../civil-ai-agent/.env.local && set +a
export CIVILAI_AGENT_HARDENING=1
unset CIVILAI_DRAFT_PIPELINE
export CIVILAI_DATA_API_BASE=http://100.48.24.128:8000
export CIVILAI_DATA_API_TIMEOUT=180
export AWS_PROFILE=civilai

uv run python bake_off.py --hardening \
  --corpus config/corpus.json \
  --batch-id uat-baseline-live-agent-full20-haiku-h1-20260709 \
  --model-id us.anthropic.claude-haiku-4-5-20251001-v1:0

uv run python judge_batch.py uat-baseline-live-agent-full20-haiku-h1-20260709 --rerun \
  --provider bedrock --model-id us.anthropic.claude-sonnet-4-6
uv run python analyze_judge_batch.py uat-baseline-live-agent-full20-haiku-h1-20260709
```

Compare `ANALYSIS.md` MISS count vs baseline. Merge gate: MISS ≤ 3 without new resolve failures.

## Parallel work (civil-ai-data)

Lake/resolver tickets for the 7 baseline MISS parcels — separate PRs, re-run eval after merge.

## H4 — Extend hardening (environmental + utilities)

Reuse pipeline dispatch/render for **environmental** and **utilities** (same as zoning/flood).

## H4.2 — P0 false-claim gates (utilities + jurisdiction)

- **Utilities:** provider names only when `*_ccn_overlay_observed` quality flag is set;
  distant main (≥500 ft) → do not assert OSSF not required; fact-echo on OSSF denial /
  unconfirmed Austin Energy.
- **Environmental / flood:** non-CoA municipal full-purpose cities (Elgin, etc.) →
  `*.jurisdiction_pending` — do not apply Travis/COA Edwards, CWQZ, or FEMA-only templates.

## Eval policy — train vs holdout vs full-20

| Corpus file | Cases | Use |
|-------------|------:|-----|
| `config/corpus_holdout.json` | **4** | **Blind test** — never tune patterns/dispatch against these SME texts |
| `config/corpus_train.json` | **16** | **Train/dev** — iterate dispatch, playbooks, lake fixes here |
| `config/corpus.json` | **20** | **Full milestone** — regression signal only after train+holdout gates pass |

**Yes, you should use train/holdout.** Full-20 runs (baseline, H1) are useful for
plumbing and milestone dashboards, but **merge decisions** should use:

1. **Holdout-4** after every change (cheap, ~4 min bakeoff + judge)
2. **Train-16** when iterating dispatch/playbooks (warm dev — not the merge gate)
3. **Full-20** at phase boundaries (H4 complete, pre-merge)

Three cases in full-20 are `judge_skip` (2 data-gaps, 1 non_comparable) → **68 judged cells**
when 17 cases resolve.

### H4 re-run commands

```bash
# Holdout gate (merge decision)
uv run python bake_off.py --hardening \
  --corpus config/corpus_holdout.json \
  --batch-id uat-hardening-h4-holdout-YYYYMMDD

# Train iteration
uv run python bake_off.py --hardening \
  --corpus config/corpus_train.json \
  --batch-id uat-hardening-h4-train-YYYYMMDD

# Full milestone (optional)
uv run python bake_off.py --hardening \
  --corpus config/corpus.json \
  --batch-id uat-baseline-live-agent-full20-haiku-h4-YYYYMMDD
```

Compare holdout `ANALYSIS.md` to baseline holdout (88%, 2 MISS on live loop).

## Phases after H4

| Phase | Work |
|-------|------|
| H5 | FE `status: blocked` UX for gated artifacts |
| Merge | Make hardening default when holdout MISS ≤ baseline |
