# Agent Knowledge Sources — Unstructured Layer

*The Civil Analyst agent already retrieves **structured** facts (parcel, zoning, flood,
watershed, utility CCN) from `civil-ai-data`. This layer adds the **unstructured /
semi-structured** knowledge it also needs — codes, manuals, agency guidance, project
documents, prior reports, technical references — with the metadata to know how far each
one can be trusted. Code: `src/civilai_agent/knowledge/`. Seed:
`src/civilai_agent/knowledge/data/knowledge_sources.yaml`.*

This is the **foundation only**: registry, models, retrieval policy, ingestion *contracts*,
seed config, tests. It deliberately ships no web crawler, no scraper, no embedding pipeline,
and no automated legal interpretation. See "What this is not" at the bottom.

---

## Why we separate sources by category and authority

A feasibility study is a regulated deliverable a P.E. signs. The single worst failure mode
is citing the wrong *kind* of source as if it were authority — e.g. concluding "wastewater
is available" from a blog, or "this is feasible" from a prior report. So the model carries
**two independent axes** for every source, and never collapses them:

- **Authority** (`AuthorityLevel`) — *how much weight a source may carry, and whether it
  can decide a final finding at all.* Regulatory code outranks everything; a prior report,
  a blog, or a public-notice agenda can **never** decide, no matter how relevant.
- **Retrieval priority** (`RETRIEVAL_PRIORITY`, category-derived) — *what to surface first*
  for a specific parcel. A project's own survey/title/will-serve letter comes **first**
  because for *this* site its own records are the most relevant evidence — even though a
  regulatory manual has higher *authority*.

These are genuinely different. A utility **will-serve letter** and a published utility
**service policy** can share the `utility_provider_records` category but have different
authority (`project_specific` vs `agency_guidance`). Keeping the axes separate is what lets
the agent surface the letter first *and* still know only current code can finalize a claim.

We also keep **separate retrieval indexes** (one per category) rather than one blended
vector store, so a search for drainage criteria can't accidentally pull an engineering blog
into the same ranked list as the adopted Drainage Criteria Manual.

## The nine categories and eight authority levels

| Category (retrieval index) | Typical authority | Can finalize a finding? |
|---|---|---|
| `regulatory_authority` | `regulatory` | ✅ when current + jurisdictionally applicable |
| `public_cases` | `official_record` | ✅ (record of fact; PE confirms interpretation) |
| `agency_guidance` | `agency_guidance` | ⚠️ supports, but process guidance ≠ final determination |
| `project_records` | `project_specific` | ✅ for this project; PE confirms capacity/engineering judgment |
| `utility_provider_records` | `agency_guidance` *or* `project_specific` | depends on the item (policy vs. letter) |
| `prior_reports` | `prior_report` | ❌ **never** — precedent + drafting language only |
| `environmental_technical` | `technical_reference` | ❌ explanation only; can't override adopted code |
| `secondary_explainers` | `secondary` | ❌ background/terminology only |
| `alerts` | `alert` | ❌ a pointer to go verify; expires when stale |

Authority order (highest → lowest, `AUTHORITY_RANK`): `regulatory` → `official_record` →
`agency_guidance` → `project_specific` → `prior_report` → `technical_reference` →
`secondary` → `alert`.

## Which sources can support a final feasibility determination

A source may back a **final** finding only if **all** hold (`can_support_final_finding()`):

1. its `can_support_final_finding` flag is set, **and**
2. its authority level is one that may decide — i.e. **not** `prior_report`, `secondary`,
   or `alert` (this is enforced at load: a config marking those final-capable **fails to
   load**), **and**
3. it isn't age-stale — a code you haven't re-verified past its refresh window is not safe
   to cite as current.

Everything else is *supporting* evidence: it can inform the draft, populate `data_gaps` /
`open_questions`, and be cited as "similar prior reports handled this by…", but it cannot be
the `controlling_source` of a finding.

## How the agent should cite sources — the evidence contract

Every finding the agent emits should be an `AgentFinding` (see `source_models.py`). It ties
`finding_text` to `evidence_items` (each pinned to a `source_id` + its authority), names a
`controlling_source`, and carries `assumptions`, `open_questions`, `requires_human_review`,
and `recommended_next_action`. The model **enforces in code**:

- `controlling_source` must be one of the finding's own evidence items.
- `controlling_source` can never be a `prior_report` / `secondary` / `alert` source.
- A finding with no final-authority evidence **must** set `requires_human_review=true`.

This mirrors the product's load-bearing rule everywhere else: **the rule engine / adopted
authority decides; the LLM narrates, cites, and flags.** The knowledge layer cannot become a
back door around it.

## Retrieval priority order (what the agent reaches for, in order)

A. Project-specific records for this parcel/project
B. Current adopted code / manuals / ordinances
C. Official agency & public records
D. Official agency guidance / checklists
E. Utility / fire / agency correspondence
F. Prior ATX Civil reports — precedent & drafting language only
G. Technical references — explanation
H. Secondary explainers — background only
I. Alerts / public notices — only to flag possible changes

`rank_sources(registry, query)` returns applicable sources in exactly this order (then by
authority, then fresh-before-stale). `final_finding_candidates(...)` narrows to the subset
that may actually decide.

## How prior feasibility reports should — and should not — be used

Prior ATX Civil reports are one of our best assets for *drafting*: they encode house style,
section skeletons, and precedent (see `feasibility-playbook/`, which proved ~89% of study
content is jurisdiction-keyed template assembly). The agent **should** lean on them for
language and "how did we handle a similar site." The agent **must not** treat them as
authority — a prior report can be wrong (the corpus contains real recurring SME errors: HSG
D mislabeled "well-drained", an Elgin FIRM cited as "Travis County", an IFC-edition
self-contradiction). Generate from current authority; emulate the *structure*, not the
errors. This is enforced: `prior_report` authority can never be a `controlling_source`.

## Why social media is excluded (except official agency alerts)

Random social posts, Reddit, Nextdoor, X, Facebook comments, citizen complaints — **never**
factual evidence. The only social content admitted is an **official agency account**
(Austin, Travis County, TxDOT, LCRA, TCEQ, FEMA, a utility, an ESD), and even then only as
an `alert` — a pointer that something may be changing, to be verified against adopted
authority. Alerts expire when stale and can never finalize a finding.

## How to add a new source

Append an entry to `data/knowledge_sources.yaml`. Required: `source_id`, `name`,
`source_category`, `authority_level`. Everything else is optional but strongly encouraged —
especially `applicable_domains`, `applicable_counties`/`applicable_cities`,
`refresh_cadence`, and `can_support_final_finding`. The registry validates on load:

- duplicate `source_id` → error;
- `supersedes_source_id` must reference a known source;
- a non-final authority marked `can_support_final_finding: true` → error;
- `retrieval_indexes` defaults to the category's canonical index if omitted; set it
  explicitly (a list) to place a source in more than one index.

Geography tokens (counties/cities/ETJ) are lowercased for matching. A source with **no**
geography is treated as applying everywhere (e.g. FEMA NFIP, NOAA Atlas 14).

## How to keep sources fresh (staleness)

`refresh_cadence` drives `is_stale(as_of)`:

| Cadence | Meaning | Stale after |
|---|---|---|
| `never` | immutable snapshot (a prior report) | never |
| `on_upload` | project file — track dates, don't refresh | never |
| `weekly` | permit/case records, alerts | 7 days |
| `monthly` | public records | ~31 days |
| `quarterly` | utility policies, agency guidance | ~92 days |
| `on_version_change` | codes/manuals — poll for a new adopted version | ~31 days (recheck heartbeat) |

`registry.stale_sources(as_of)` lists scheduled sources past their window. A stale
*regulatory* source stays visible to the agent (so it knows the code exists) but drops out
of `final_finding_candidates` until re-verified. Alerts with `expiry_policy: expire_when_stale`
disappear from retrieval entirely once stale.

## What this is not (out of scope for this foundation)

Deliberately **not** built here: full web crawling, social-media scraping, automated legal
interpretation, automatic report finalization without human review, unbounded agency-site
scraping, and any concrete embedding/vector backend. The heavy ingestion pipeline, when
built, lives behind the `ingestion_contracts.py` Protocols (`DocumentLoader`, `Chunker`,
`ChunkIndex`) — and most likely in the data/platform layer, not here. This repo owns the
*contract and the policy*; the agent can be written and tested against fakes today.
