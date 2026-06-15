# Data Catalog

## Purpose

This document summarizes what the agent should expect from the backend data platform and
where the data remains partial, missing, user-supplied, or source-tool dependent.

For API alignment and proposed gaps, see [Data Alignment](data-alignment.md).

## Backend Contract

The agent should use BE APIs and service facts rather than directly reading raw S3 data.
The backend owns:

- S3 source/raw data.
- Curated parquet datasets.
- Current relations.
- `svc_section_*` service views.
- Entity resolution.
- Section facts.
- Provenance.
- Project snapshots.
- Exports.

## Section IDs

Current BE section IDs:

- `parcel-overview`
- `zoning`
- `flood`
- `jurisdiction`
- `watershed`
- `soils`
- `utilities`
- `mobility`
- `environmental`
- `compliance`
- `provenance`

These backend sections do not map one-to-one to the ATX Civil report sections. The
agent should assemble report sections from multiple BE sections plus user input,
uploaded documents, rule tools, and SME assumptions.

## Coverage Summary

| Domain | Current agent posture |
| --- | --- |
| Parcel/entity | Use BE as primary source. Preserve ambiguity and snapshot metadata. |
| Jurisdiction | Use BE as primary source, but surface coverage limits and ETJ ambiguity. |
| Zoning | Strongest where overlay-backed data exists; otherwise route to jurisdiction source. |
| Flood | Use BE flood facts, but confirm FIRM panel/effective date availability. |
| Watershed | Use BE watershed facts; supplement with local rule tables/manuals. |
| Soils | Use BE/SSURGO facts where available; cite source and coverage percentages. |
| Utilities | Use BE provider/CCN coverage only. Never infer capacity or will-serve. |
| Mobility/ROW | Treat as partial until road authority, ROW width, and standards are confirmed. |
| Environmental | Treat as layered/partial; use source-specific caveats. |
| Compliance | Treat derived outputs as rules-based and citation-required. |
| Provenance | Required for report-ready claims and source bundles. |

## Data Categories

### BE-Backed Facts

Facts returned by BE APIs with source/status/provenance. These are preferred inputs.

### Derived Facts

Facts computed from BE-backed or source-backed inputs using explicit rules.

Examples:

- Controlling impervious cover limit.
- OSSF minimum lot-size pass/fail.
- Likely TxDOT driveway permit dependency.
- Permit checklist candidates.

Derived facts must include inputs, rule, citation, and result.

### Source-Tool Facts

Facts retrieved from public sources, uploaded documents, manuals, GIS viewers, or
jurisdiction portals because BE does not yet contain them.

### User/SME Inputs

Facts or assumptions provided by the analyst or SME.

Examples:

- Proposed use.
- Unit count/building size.
- Site layout.
- Fire flow test result.
- Provider communication.
- Title/survey interpretation.

### Data Gaps

Missing, partial, ambiguous, unavailable, or insufficient information needed for a
section, risk, or recommendation.

## High-Value Missing Or Partial Data

These data needs are especially important for the agent:

- Proposed development program.
- Utility capacity and will-serve confirmation.
- Water/wastewater line size, material, and distance to main.
- Fire jurisdiction, adopted IFC edition, and fire flow result.
- Plat status and recorded plat documents.
- Title commitment, easements, and deed restrictions.
- Survey-based acreage and boundary evidence.
- Road classification, ROW width, maintenance authority, and dedication requirement.
- TxDOT driveway permit applicability.
- FIRM panel number and effective date where not surfaced.
- Edwards/TCEQ zone and regulated-activity determinations where not surfaced.
- Jurisdiction-specific impervious cover, WQ, detention, and drainage rule tables.
- Exhibit manifest and source linkage.

## Report-Ready Claim Rules

A claim is report-ready only when it has:

- Source or assumption support.
- Status.
- Freshness/snapshot where applicable.
- Citation or source reference.
- Clear caveat if partial or uncertain.
- Review state.

Claims that do not meet this standard can still exist as draft findings or data gaps,
but should not be presented as final report language.

## Utility Rule

Provider coverage, CCN territory, or service area is not capacity and not will-serve.

The agent may say:

```text
The site is within the mapped service territory of [provider].
```

The agent must not say:

```text
Water and wastewater capacity is available.
```

unless capacity is confirmed by provider evidence or a source-backed engineering study.

## Geography/Coverage Rule

The agent must describe coverage limits in plain language. If a county or jurisdiction
has parcel-only or partial data coverage, the agent should say so and route the analyst
to the appropriate source or follow-up action.
