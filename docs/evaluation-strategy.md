# Evaluation Strategy

## Purpose

The Civil AI Agent should be evaluated as a professional workbench assistant, not only as
a conversational model. The evaluation program must test factual grounding,
inspectability, section quality, workflow usefulness, and SME trust.

## Evaluation Assets

### Golden Feasibility Studies

Use real customer feasibility studies as reference material. Convert them into
evaluation cases with:

- Project metadata.
- Proposed use.
- Jurisdiction.
- Key facts.
- Final feasibility posture.
- Critical constraints.
- Required actions.
- Exhibits used.
- Known template deviations.

### Source Bundles

For each evaluation case, assemble source bundles:

- BE facts and provenance.
- Extracted report text.
- Template section.
- Source documents.
- Exhibits/maps where available.
- Known SME notes or assumptions.

### Section Benchmarks

Create per-section tests for:

- Zoning.
- Platting.
- Watershed.
- Impervious cover.
- Utilities.
- Utility capacity.
- ROW/access.
- Floodplain.
- Drainage criteria.
- Easements/setbacks.
- Water quality/detention.
- Transportation.
- Summary.

## Evaluation Dimensions

| Dimension | Question |
| --- | --- |
| Fact grounding | Are factual claims supported by BE facts, documents, or cited sources? |
| Source traceability | Can the analyst inspect where each claim came from? |
| Status handling | Does the agent preserve partial/ambiguous/unavailable statuses? |
| Caveat quality | Are uncertainties stated clearly and professionally? |
| Feasibility reasoning | Does the agent identify real blockers and conditions? |
| Section fit | Does the output match the purpose of the report section? |
| Template judgment | Does the agent know when to follow or deviate from the template? |
| Utility discipline | Does the agent avoid confusing provider coverage with capacity? |
| Actionability | Does the agent recommend the right next steps? |
| Workbench usefulness | Can outputs be saved, edited, reviewed, and reused? |

## Automated Checks

Automated tests should flag:

- Claims without source references.
- Regulatory values without rule citations.
- Utility capacity overclaims.
- Missing data presented as known fact.
- "Feasible" summary when critical sections are unresolved.
- Contradictions across sections.
- Report sections without required action/caveat when status is partial.
- Unsupported template placeholders.
- Drafts that cite conversation history rather than saved facts or assumptions.

## Human SME Review

SMEs should review sampled outputs for:

- Correct feasibility posture.
- Correct prioritization of constraints.
- Professional tone.
- Appropriate caveats.
- Missing or excessive detail.
- Whether the output would reduce analyst effort.
- Whether a deviation from the template is justified.

## Regression Suites

Create stable regression cases for high-risk patterns:

- OSSF infeasible due to lot size.
- Public wastewater unavailable but service territory present.
- FEMA Zone AE requiring floodplain study.
- Zone X with no flood study expected.
- Edwards Aquifer Contributing or Recharge Zone.
- TxDOT frontage and driveway permit dependency.
- Pipeline/drainage easement layout constraint.
- Jurisdiction/ETJ ambiguity.
- CAD acreage vs survey discrepancy.
- Missing title commitment.
- Customer-specific feasibility question.

## Metrics

Quantitative metrics:

- Unsupported claim rate.
- Required citation coverage.
- Correct data status preservation.
- Correct feasibility posture rate.
- Correct blocker identification rate.
- Section completeness score.
- SME edit distance or revision burden.
- Time to first usable artifact.

Qualitative metrics:

- SME trust.
- Analyst usefulness.
- Explanation clarity.
- Trace inspectability.
- Recommendation usefulness.

## Evaluation Loop

1. Run agent against benchmark case.
2. Capture output, artifacts, tool trace, sources, and data gaps.
3. Run automated checks.
4. SME reviews selected outputs.
5. Convert corrections into:
   - Tool changes.
   - Prompt/policy changes.
   - Section playbook updates.
   - Backend data/API requests.
   - New regression tests.

## Release Gates

Before pilot:

- No known utility capacity overclaiming.
- Source references present for all material claims.
- Data gaps visible for partial and unavailable fields.
- SME review workflow exists.
- At least one regression suite covers major infeasibility patterns.

Before production:

- Role-gated approval states.
- Durable artifact store.
- Trace retention policy.
- Evaluation dashboard or repeatable CI process.
- Documented data/source coverage limits by geography.
