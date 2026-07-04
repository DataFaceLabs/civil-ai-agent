# Playbook Integration Plan — Sequential, One Rule at a Time

*How we port the validated `feasibility-playbook/` decision procedures into the agent
**without regressing**. This is the detailed execution plan behind
`agent-tuning-strategy.md` Phase 2.5. The governing principle is deliberate slowness: one
rule, in one section, validated against the real corpus, in its own PR — never a batch.*

---

## Why one at a time

The playbook is validated **in aggregate** (89% PARTIAL-or-better across 120 blind-scored
holdout cells) — but that is not the same as "every rule is safe to ship." Its own
`README.md` lists specific **amendments required before agent use** (the §212.004
plat-exemption gate is wrong; floodplain-study dispatch keys on the wrong variable; the OSSF
lot-size gate needs an "existing OSSF retained" exception; the TIA trigger over-fires in
CoA). Each of those is a rule that is *mostly* right and *specifically* wrong in a way that
matters. Shipping them as a batch would make a regression impossible to attribute.

We already have direct evidence this is the right caution. The eval harness caught a live
self-contradiction in the zoning draft (the model recited "Texas counties have no zoning"
for a City-of-Austin-limited-purpose parcel) that traces partly to a **starter pattern I
wrote that only handled two of the three jurisdiction cases** (see item Z-1 below). A
one-rule-at-a-time cadence is what surfaces that instead of burying it.

## Two layers — deterministic first, prose second

Every playbook rule lands in exactly one of two places. Get this split right per rule:

| Layer | Where | What belongs here | Validation |
|---|---|---|---|
| **Deterministic** | `civil-ai-data` determination YAMLs (`docs/design/section_determinations/*.yaml`) + the rule engine | Anything that decides a branch from facts: lot-size gates, threshold triggers, exemption logic, classification bands. **The rule engine decides; the agent narrates.** | rule-engine contract tests + determination-coverage gauge |
| **Prose** | `civil-ai-agent` structured-draft prompt / section patterns | Jurisdiction-keyed boilerplate stems, branch-selection *narration*, house style. Never a determination. | eval harness / golden suite (Tier R + J) |

**Order within a rule: deterministic half first.** If a rule has both a gate and a stem
(most do), port the gate into the YAML and prove it in the rule engine *before* touching the
prompt — so the model drafts against a corrected determination, never a stale one. A prose
stem written against a wrong gate just launders the wrong answer into nicer language.

## The per-rule validation loop (the gate)

For **each** rule, in its own branch and PR:

1. **Write the rule** in its layer (YAML gate, or prompt stem — not both in one PR unless
   they're inseparable).
2. **Unit-prove it.** Deterministic: a rule-engine contract test with the exact
   inputs→branch it must produce, including the counterfactual (the input that flips it).
   Prose: a golden/eval assertion (Tier R once Phase 2 exists).
3. **Validate against the real corpus** — the load-bearing step. Run the eval harness on the
   holdout case(s) the playbook cites for this rule (each amendment names its evidence, e.g.
   Bullick for floodplain-study dispatch, Nixon for the AO sliver, 2121-Howard for the OSSF
   distance trap). Confirm the draft now matches the SME study's branch **and** that no other
   section regressed.
4. **Smoke-test the whole section set on the feature branch before the PR to `develop`**
   (per the standing rule added this cycle). A rule change is not "done" until a
   full-section smoke run on the branch is clean.
5. **One PR, one rule.** Merge only if steps 2–4 are green. Then the next rule.

**Interim vs. target validation:** until Phase 2's golden suite exists, step 3 is a *manual*
diff of the harness `run.md` against the real study for 2–3 named cases (what we do today).
Once Tier R lands, step 3 becomes an automated gate. Do **not** wait for the suite to start
the deterministic (YAML) rules — those are provable in the rule engine today. Do **not**
start the prose stems' model A/B until the suite exists (tuning without a scoreboard is the
trap the audit named).

## Sequenced backlog

Ordered by (a) safety leverage and (b) dependency. Each item: **layer**, **playbook
source**, **acceptance case(s)**, **status**. Sections grouped; within a section, do the
deterministic gate before the stem.

### Utilities / OSSF (highest safety leverage — the coverage≠capacity section)

- **U-1 · OSSF lot-size gate** — *deterministic.* Playbook 04: `<1.0 ac infeasible /
  1.0–1.5 ac advanced / ≥1.5 ac conventional`, **with an "existing OSSF retained"
  exception** (Bullick, 0.925 ac, feasible). Today `utilities.yaml`'s `wastewater_service`
  only gates on the `ossf_required` boolean — no lot-size logic at all. **Acceptance:**
  Bullick (0.925 ac + existing OSSF → feasible), a <1.0 ac no-OSSF case → infeasible,
  ≥1.5 ac → conventional. **Blocked on** the `wastewater_distance_to_property` field
  (P1 data gap, `data_requirements.md`) for the distance half; the lot-size half is doable
  now. **Status: not started.**
- **U-2 · will-serve vs. coverage stem** — *prose.* Already partly enforced by the F3
  guardrail fix + the harness `utilities.md` pattern. Formalize the stem in the prompt.
  **Acceptance:** 2121-Howard utilities draft never asserts availability from a territory
  match. **Status: pattern exists (harness only), not in the agent prompt.**

### Zoning / Jurisdiction

- **Z-1 · CoA limited-purpose branch** — *prose.* The starter `zoning.md` pattern handles
  only "Travis County unincorporated (no zoning)" and "CoA full purpose" — it has **no
  branch for CoA *limited* purpose**, which is where the live self-contradiction came from
  (2121-Howard). Add the third branch and an explicit instruction to defer to governed
  `jurisdiction_primary` / `zoning_code` over any general jurisdictional assumption.
  **Acceptance:** 2121-Howard zoning draft states CS zoning without denying zoning applies.
  **Status: not started — earliest prose item; low risk, high clarity.**
- **Z-2 · rezoning-required trigger** — *deterministic.* Playbook 02: the permit assembler
  needs a rezoning-project trigger. **Acceptance:** a parcel whose proposed use isn't
  permitted by the district surfaces the rezoning process and does not read "feasible."

### Platting / Compliance

- **P-1 · §212.004 plat-exemption gate** — *deterministic.* Playbook 02: the current gate is
  wrong (the SME granted the exemption inside a full-purpose city; add the
  unrecorded-subdivision branch). **Acceptance:** the playbook's cited full-purpose-city
  case resolves to the correct plat requirement. **Status: not started.**

### Floodplain / Drainage

- **F-1 · floodplain-study dispatch by work-scope** — *deterministic + prose.* Playbook 03:
  dispatch keys on **proposed-work scope, not FEMA zone** (Bullick in AE got FS1 only;
  Nixon's AO sliver got the full FS4/LOMC block). **Acceptance:** Bullick → FS1, Nixon →
  FS4. **Status: not started; needs proposed-use/work-scope input (also a data gap).**
- **F-2 · CWQZ setback bands** — *already shipped* in `civil-ai-data` (IMPACT D6, TC
  §482.941, holdout-confirmed). Listed here only to record it's done and validated.

### Summary / Recommendations

- **S-1 · overall feasibility posture** — *deterministic (composite).* Gated by
  **`civil-ai` ADR-0005** (no posture section exists yet) and by Phase 2 (must be validated
  against 509-Cresthill's real infeasible verdict before shipping). Not a playbook stem —
  a composite determination. **Status: documented, deliberately deferred.**

## Process guardrails (do not skip)

- **One rule → one PR → one smoke test.** No batching. The whole point is attributable
  regressions.
- **Deterministic before prose**, always, within a rule.
- **Never ship a stem written against an unproven gate.**
- **Don't start the model A/B (Haiku/Sonnet/Nova/Kimi) until the golden suite exists** and
  at least the U-1/Z-1/P-1 rules are in — comparing models before the agent has the
  validated patterns tests the wrong thing (Phase 2.5).
- **Emulate the structure, not the errors.** The corpus contains real recurring SME
  mistakes (HSG D mislabeled "well-drained", an Elgin FIRM cited as "Travis County"). Every
  ported rule generates from current governed facts; it never reproduces a known corpus
  error just because the playbook stem happened to include it.

## Dependencies at a glance

```
Golden eval suite (Phase 2, 509-Cresthill first)
   └── gates automated validation for ALL prose rules (U-2, Z-1, ...)
   └── gates S-1 (posture) entirely

Data gaps (civil-ai-data, data_requirements.md P1)
   └── ww_main_distance  --> blocks U-1 distance half, F-1 fully
   └── proposed work-scope --> blocks F-1

ADR-0005 (posture section)  --> blocks S-1

Deterministic gates with no data dependency (do these first):
   U-1 lot-size half, Z-2, P-1  -- provable in the rule engine today
Prose stems with no data dependency:
   Z-1 (limited-purpose branch), U-2  -- provable via the harness today
```
