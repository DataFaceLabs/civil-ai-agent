# Data Alignment

## Purpose

This document maps the Civil AI Agent's needs to the backend data architecture, S3
serving model, current APIs, frontend workbench context, and known data gaps.

The agent should not be designed around raw files. It should be designed around stable
project, entity, section fact, provenance, and artifact contracts.

## Backend Data Architecture Summary

The backend is the governed data platform. Its data architecture is medallion-like:

```text
source/raw data in S3
  -> curated parquet datasets
  -> current relations
  -> svc_section_* service views
  -> FastAPI facts/provenance/project APIs
```

The agent should treat the service views and APIs as the supported surface. Direct S3
access should be reserved for backend jobs, debugging, or explicitly approved tools.

## Current API Surfaces The Agent Should Use

| Agent need | Preferred BE surface | Notes |
| --- | --- | --- |
| Resolve address or parcel | `/v1/entities/resolve` | Start here for address/parcel ambiguity. |
| Fetch one section | `/v1/sections/{section_id}/facts/{entity_id}` | Best for section-specific drafting. |
| Fetch all facts | `/v1/entities/{entity_id}/facts` | Best for project-wide investigation. |
| **Run determinations (the derivation layer)** | `/v1/entities/{entity_id}/determinations` | **Deterministic** findings (applicability/decision/conclusion) with `inputs_used`, rule basis, and confidence. The agent's derivation layer — see below; do not re-derive in the agent. |
| Inspect evidence lineage | `/v1/entities/{entity_id}/provenance` | Needed for claims, citations, and traceability. |
| Export evidence | `/v1/entities/{entity_id}/export` | Useful for source bundles and QA packets. |
| Create/retrieve parcel snapshot | `/v1/parcel-snapshots`, `/v1/parcel-snapshots/{id}` | Pins serving `snapshot_date` for reproducible exports. |
| Export parcel snapshot | `/v1/parcel-snapshots/{id}/export` | Useful for report assembly and review at a pinned date. |
| FE site lookup | `/v1/fe/site/by-address`, `/v1/fe/site/by-parcel` | Current FE-oriented parcel/site bootstrap. |
| Catalog discovery | `/v1/catalog/*` | Useful for runtime schema awareness. |
| Legacy report workflow | `/report`, `/report/{run_id}/domain/{n}` | Compatibility path, not preferred new design. |

## Derivation Layer: The Determination Engine (deterministic)

The proposed `POST /v1/derivations/evaluate` (see [API Gaps](#api-gaps-to-consider)) is
**already built.** `civil-ai-data` exposes a **determination engine** at
`GET /v1/entities/{entity_id}/determinations`, which evaluates the section-determination
contracts (platting, zoning, flood, jurisdiction, environmental, soils, utilities, watershed,
mobility, compliance) over a parcel's served facts and returns **determination records**:
`{determination_id, inquiry, branch, conclusion, confidence, inputs_used}`. Each record already
satisfies the [Data Rules](#data-rules) — input values, the rule applied (`basis`), the result,
and confidence.

**This is the agent's derivation layer — and it is deterministic Python, not the LLM.** The
"Derivation Tools" the agent needs (controlling impervious-cover limit, OSSF applicability, plat
exemption, SFHA status, permitting authority, Edwards WPAP/CZP, …) are **determinations, not
prompts.** The agent *calls* them; it does not re-derive that logic.

### Deterministic vs LLM — the contract

| Done deterministically (Python / the engine) | The LLM's job — the only place it earns its cost |
| --- | --- |
| Resolution, fact + provenance retrieval | Understanding open-ended natural-language requests |
| **All determinations** (the contract set) | **Synthesizing** determination records into report-quality, ATX-voice prose |
| Citations / claim → source · gap detection | What-if / scenario reasoning over the deterministic outputs |
| Permit-checklist rules · templated conclusions | Extracting facts from **unstructured** evidence (uploaded docs, code/manual text) |
| Grounding QA · confidence → SME routing | Conversational explanation / Q&A |

Rule of thumb: **if the agent is asked to *decide* a determination, that is the signal to move
it into the engine.** (Example: impervious-cover limit is the most-restrictive of
zoning/watershed/overlay — a deterministic rule, never an LLM call. Get the input facts into the
lake; the limit is a determination.)

### Call pattern — pre-compute, then synthesize (cost + latency)

Prefer a **deterministic pre-compute → bounded LLM synthesis** pipeline over an open-ended
"LLM reasons in a loop, calling tools one at a time" pattern:

1. Deterministically run resolve → facts → **all determinations** → gaps → permit rules
   (zero LLM) into a structured *evidence packet*.
2. Make a **small, fixed number of LLM calls** (ideally one structured call, or one per report
   section) to synthesize that packet into narrative, over **prompt-cached** context.

Two modes, deliberately separated: **study generation** (the batch pipeline above — predictable,
low LLM-call count, reproducible) and **interactive Q&A** (an LLM tool-calling loop, only for
ad-hoc questions you cannot pre-compute). At scale the determinations are ~free (cached Athena);
the LLM is the cost driver, so bound it — few calls per study, prompt caching, a cheaper model
for routing/extraction with the strong model only for synthesis, parallelized per section.

## Section Fact Catalog

The current BE section catalog contains these section IDs:

| Section ID | Agent interpretation |
| --- | --- |
| `parcel-overview` | Address, parcel identity, acreage, county, legal/CAD context. |
| `zoning` | Zoning and overlay facts where available. |
| `flood` | FEMA/NFHL flood facts and risk flags. |
| `jurisdiction` | City, ETJ, county, authority, and coverage facts. |
| `watershed` | Watershed, HUC, classification, and related drainage context. |
| `soils` | SSURGO soil and hydrologic group facts. |
| `utilities` | Provider/service territory facts, not capacity confirmation. |
| `mobility` | Transportation, access, ROW, and mobility context where available. |
| `environmental` | Environmental constraints and protected-area facts where available. |
| `compliance` | Derived or assembled compliance posture where available. |
| `provenance` | Source, status, freshness, and lineage. |

The agent should map these backend sections to the ATX Civil report sections. They are
related but not one-to-one.

## Status Semantics

The agent must preserve source/status semantics from BE:

| Status | Agent behavior |
| --- | --- |
| `complete` | Can draft with normal confidence and citations. |
| `partial` | Draft with caveats and list missing values. |
| `ambiguous` | Ask for analyst resolution or present alternatives. |
| `unavailable` | State unavailability and suggest source/action. |
| `not_applicable` | Do not force template language for irrelevant sections. |
| `insufficient_data` | Do not infer; create a data gap and next action. |

## Feasibility Section Mapping

| Report section | Primary BE facts | Other inputs needed |
| --- | --- | --- |
| 2.1 General Information | `parcel-overview`, `jurisdiction` | Proposed use, client/project details, uploaded survey/title if available. |
| 2.2 Site Characteristics | `soils`, `watershed`, `environmental` | Terrain/slope, ecoregion, site observations, exhibit references. |
| 2.3 Property Identification | `parcel-overview`, `provenance` | CAD owner/deed details, discrepancies, title commitment. |
| 3.1 Zoning | `zoning`, `jurisdiction` | Proposed-use fit, overlays, jurisdiction code lookup. |
| 3.2 Platting | `parcel-overview`, `jurisdiction` | Clerk/plat records, subdivision intent, LSD/plat exemption logic. |
| 3.3 Watershed | `watershed`, `environmental` | Edwards/TCEQ zone, Barton Springs Zone, local watershed rules. |
| 3.4 Impervious Cover | `zoning`, `watershed`, `compliance` | Rule tables, proposed IC, controlling standard. |
| 3.5 Utility Location and Availability | `utilities` | Line size/location, distance to mains, provider contacts, OSSF logic. |
| 3.6 Utility Capacity | `utilities` | Provider confirmation, fire flow test, SER/capacity study status. |
| 3.7 Right of Way | `mobility`, `jurisdiction` | Road classification, ROW width, TxDOT/city/county standards. |
| 3.8 FEMA/Floodplain Maps | `flood` | FIRM panel/effective date, exhibit reference. |
| 3.9 Floodplain Study | `flood`, `watershed`, `environmental` | Atlas 14, EHZ/CWQZ, local drainage criteria. |
| 3.10 Drainage Area Map | `watershed`, `flood` | Drainage basins, survey/topo, site layout. |
| 3.11 Adjacent Sites | `parcel-overview`, `zoning` | Neighboring land use, aerial review, compatibility context. |
| 3.12 Compatibility | `zoning`, `jurisdiction` | Adjacent uses, proposed building height/use, local standards. |
| 3.13 Governing Jurisdictions | `jurisdiction` | Fire authority, utility authorities, de-annexation, ETJ details. |
| 3.14 Development Agreements | `jurisdiction`, `provenance` | Public-record search, title commitment, clerk records. |
| 3.15 Drainage Design Criteria | `watershed`, `flood`, `jurisdiction` | Applicable manuals, Atlas 14, local detention/WQ rules. |
| 3.16 Easements and Setbacks | `parcel-overview`, `zoning`, `flood` | Survey/title, easements, pipelines, waterway setbacks. |
| 3.17 Water Quality and Detention | `watershed`, `environmental`, `compliance` | WQ/detention requirements, BMP rules, LCRA/CoA/local manuals. |
| 3.18 Transportation | `mobility`, `jurisdiction` | TIA thresholds, driveway permits, sidewalks, fire access. |
| 3.19 Surveys, Title, Other Docs | `provenance` | Uploaded docs, title, survey, geotech, ERI, site plans. |
| 4.0 Summary | All sections | Feasibility posture, risks, recommendations, unresolved conditions. |

## What The Agent Needs That BE Has

The agent can already be designed around these BE-backed concepts:

- Entity resolution from address/parcel.
- Project creation and snapshot pinning.
- Section fact retrieval.
- Per-section data status.
- Provenance and export surfaces.
- Parcel overview and jurisdiction context.
- Flood, watershed, soils, utilities provider coverage, and zoning where covered.
- Service-view coverage distinctions by county and source.

## What The Agent Needs That BE Partially Has

These should be treated as partial until BE service coverage and API contracts are
confirmed:

- Terrain/slope and elevation facts.
- Road/ROW/mobility facts.
- Environmental overlays beyond core flood/watershed data.
- Compliance-derived values such as impervious-cover limits, OSSF applicability, and permit
  requirements — **the determination engine now provides these deterministically; completeness
  is gated on the input facts** (e.g. non-Austin IC code tables, Barton Springs / LCRA HLWO
  special zones, lot platting, existing on-site IC).
- Jurisdiction-specific rule tables.
- Historical snapshots for every user-facing artifact.

## What The Agent Needs That BE Does Not Yet Fully Provide

These likely need new APIs, connectors, source tools, or user-supplied inputs:

- Provider will-serve or capacity confirmation (hard non-goal — never infer from GIS).
- Fire flow test status and result.
- Fire jurisdiction/ESD and adopted IFC edition (ESD name may be served; edition often not).
- Plat status and recorded plat documents.
- Deed restrictions, title exceptions, easements (dev agreements partially served).
- TxDOT driveway permit applicability and roadway authority details.
- Proposed development program, site layout, building area, unit count, and proposed IC.
- Uploaded feasibility exhibits and customer documents.
- SME judgment calls and customer-specific questions.

**Already served (do use when present):** nearest water/wastewater main distance/diameter/material
via `nearest_*_distance_m` + `network_coverage_tier`; municipal tap cards (`tap_cards_*`);
FIRM `panel_id` / `effective_date` when coverage is live. GIS proximity and tap cards are
**not** capacity or will-serve.

## API Gaps To Consider

These are not implementation commitments, but they are likely useful agent-facing
contracts:

| Proposed API | Purpose |
| --- | --- |
| `GET /v1/projects/{id}/context` | Return a compact workbench/agent context envelope. |
| `GET /v1/projects/{id}/artifacts` | Return saved findings, risks, draft sections, and citations. |
| `POST /v1/projects/{id}/artifacts` | Save agent-created artifacts after user action. |
| `GET /v1/entities/{id}/section-map` | Map BE sections to report sections and available fields. |
| `GET /v1/entities/{id}/gaps` | Return known missing/partial data by report section. |
| `GET /v1/reference-sources` | Align with FE expectation for visible source catalog. |
| `POST /v1/evidence/search` | Search uploaded docs/source bundles by project. |
| `POST /v1/derivations/evaluate` | Evaluate rule-derived fields with citation and explanation. **Realized** as `GET /v1/entities/{id}/determinations` (the determination engine). |

## FE Data Needed By The Agent

The frontend should provide:

- Project ID.
- Entity ID.
- Snapshot date.
- Proposed use and development program.
- Active workflow step or report section.
- Selected map layers.
- Selected source documents or exhibits.
- User edits and notes.
- SME approvals/rejections.
- Current artifact selection.
- Role/permission context.

## Data Rules

- Service territory/provider coverage is not capacity and not will-serve.
- CAD acreage is not a substitute for survey/title when precision matters.
- Map overlays are planning evidence, not a boundary survey.
- Missing data should become a data gap, not a hallucinated conclusion.
- Derived fields must include the input values, rule applied, and citation.
- User-provided assumptions must be labeled as assumptions.
- Customer documents should be cited separately from public source records.
