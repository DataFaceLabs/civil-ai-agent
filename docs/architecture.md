# Agent Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Engineer / Reviewer                      │
│          (types address, asks questions, reviews draft)       │
└───────────────────────────┬─────────────────────────────────┘
                            │ conversation
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    AWS AgentCore                             │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                Strands Orchestrator                  │   │
│   │                                                     │   │
│   │  Session memory ◄──────► Tool registry              │   │
│   │  (parcel context,        (see tool list below)      │   │
│   │   conversation turns)                               │   │
│   │                                                     │   │
│   │        ┌──────────────────────────────┐             │   │
│   │        │     Claude claude-sonnet-4-6              │             │   │
│   │        │  (reasoning + generation)    │             │   │
│   │        └──────────────────────────────┘             │   │
│   └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         │                │               │
         ▼                ▼               ▼
  civil-ai-be        MuniCode /       TCEQ / FEMA /
  FastAPI /report    TAC viewer       permit portals
  (Athena data lake) (regulatory      (live lookups)
                      text)
```

---

## AWS AgentCore Role

AgentCore provides:
- **Managed execution environment** — scales automatically, handles session state between
  API calls
- **Tool invocation** — dispatches tool calls with schema validation, retries, and
  error surfacing to the agent
- **Access control** — IAM roles isolate the agent's read-only access to S3/Athena from
  civil-ai-be's write permissions
- **Audit logging** — all tool calls logged to CloudWatch for review and debugging

The agent is stateless between sessions. Each new study begins with a fresh context;
the engineer may resume a session using a `session_id`.

---

## Strands Orchestrator Role

Strands manages multi-step reasoning:
- Decides which tools to call and in what order for a given user request
- Chains tool outputs into context for the next reasoning step
- Manages the `{section_context}` window — passes relevant section facts to the LLM
  when generating each study section
- Handles partial data: if `query_section_facts()` returns `null` for a field, Strands
  directs the agent to either (a) fetch from a secondary source or (b) surface the gap
  to the engineer

---

## Tool Registry

Every fact asserted in generated output must be produced by a tool call —
not hallucinated from training data.

### Core Data Tools

| Tool | Source | Returns |
|------|--------|---------|
| `query_section_facts(address, section_id)` | civil-ai-be `/report` → Athena | Structured section facts + `source_refs` JSON for the requested section |
| `query_all_sections(address)` | civil-ai-be `/report` → Athena (parallel) | All 9 section fact objects for a given address, with citations |
| `get_parcel_metadata(address)` | civil-ai-be parcel endpoint | Parcel ID, acreage, legal description, CAD record, owner |

### Regulatory Lookup Tools

| Tool | Source | Returns |
|------|--------|---------|
| `fetch_ldc_section(section_id)` | MuniCode API | City of Austin LDC section text |
| `fetch_tac_section(title, chapter, section)` | Texas SOS TAC viewer | Texas Administrative Code section text |
| `fetch_travis_county_code(section_id)` | EncodePlus API | Travis County Code section text |
| `lookup_firm_panel(lat, lon)` | FEMA MSC API | FIRM panel number, effective date, flood zone |
| `lookup_fema_flood_zone(entity_id)` | civil-ai-be flood_current view | FEMA zone, floodway flag, fld_ar_id |

### Permit / Agency Lookup Tools

| Tool | Source | Returns |
|------|--------|---------|
| `search_tcad(parcel_id)` | TravisCAD search | Owner, deed doc, property values, CAD discrepancies |
| `search_tccsearch(parcel_id)` | Travis County Clerk | Plat records, development agreements, deed restrictions |
| `lookup_tceq_ccn(lat, lon)` | TCEQ CCN viewer | Water and wastewater CCN numbers and provider names |
| `lookup_edwards_aquifer_zone(lat, lon)` | TCEQ Edwards viewer | Zone (Recharge / Contributing / Transition / Outside) |
| `lookup_austin_property_profile(address)` | Austin Property Profile | Watershed, zoning, utility grid map refs, OSSF permits |
| `search_permit_records(parcel_id, permit_type)` | Austin DSD / county portals | Active permits, OSSF permit IDs, pending applications |

### Document Generation Tools

| Tool | Use |
|------|-----|
| `draft_section(section_id, facts, user_notes)` | Generate section language in ATX Civil voice |
| `generate_summary(all_sections)` | Generate §4.0 Summary with recommendations |
| `flag_infeasibility(section_id, reason)` | Surface an infeasibility signal with supporting evidence |
| `generate_gap_report(address)` | List all missing fields and their recommended sources |

---

## Session State Model

Each session carries:

```json
{
  "session_id": "uuid",
  "address": "1801 Hur Industrial Blvd, Cedar Park TX 78641",
  "entity_id": "abc12345-...",
  "parcel_context": { ...parcel metadata... },
  "section_facts": { "flood": {...}, "zoning": {...}, ... },
  "drafted_sections": { "3.1": "...", "3.2": "..." },
  "data_gaps": ["esd_number", "fire_flow_test_status"],
  "user_notes": { "3.5": "Engineer confirmed ESD#11 covers this area" },
  "conversation_history": [ ...last N turns... ]
}
```

`section_facts` is populated lazily — fetched on first reference to a section.
`drafted_sections` accumulates as the engineer requests each section.
`data_gaps` grows as tools return null values; the agent proactively surfaces these.

---

## Agent Capability Modes

### Mode 1: Conversational Q&A
User asks a question about the parcel. Agent calls the minimum necessary tools, answers
in plain language, cites source.

> "Is this property in a flood zone?"  
> → `query_section_facts(address, "flood")` → "Yes, the northwestern portion of the
> property falls in FEMA Zone AE per FIRM panel 48453C0115J (effective Jan 22, 2020).
> A fully-developed floodplain study is required."

### Mode 2: Section Draft Generation
User requests a specific section. Agent pulls all required facts, drafts language in
ATX Civil voice, presents to engineer for review.

> "Draft section 3.3 Watershed"  
> → `query_section_facts(address, "watershed")` + `query_section_facts(address, "flood")`  
> → Full watershed narrative with HUC12, Edwards Aquifer zone, watershed classification,
> WPAP flag, IC limits — all with inline citations

### Mode 3: Full Study First Draft
User requests the full study. Agent generates all 19 sections sequentially, calls
`query_all_sections()` first for efficiency, then drafts in section order using
accumulated context.

### Mode 4: Gap Discovery
User asks "what information do I still need?" Agent runs `generate_gap_report()` which
identifies all null fields and proposes specific actions (e.g., "Fire flow test not yet
ordered — contact ESD#11 to initiate").

---

## Data Flow for Section Generation

```
1. query_all_sections(address)
        │
        ▼
2. Receive structured facts + source_refs per section
        │
        ├─ For each null field:
        │    └─ Try secondary tool (permit lookup, regulatory text fetch)
        │
        ▼
3. Build section_context:
   facts + citations + user_notes + relevant regulatory text
        │
        ▼
4. draft_section(section_id, section_context)
   → Claude generates in ATX Civil voice
   → Inline citations from source_refs
   → Hedge phrases for unverified values
        │
        ▼
5. Return draft to engineer for review
   + data_gap list for any remaining null fields
```

---

## Citation Contract

Every factual value in generated text must have a citation. The citation format follows
`civil-ai-be`'s `source_refs` schema:

```json
[
  {
    "citation_type": "data",
    "source_id": "fema_nfhl",
    "source_record_id": "48453C0115J",
    "citation_url": "https://www.fema.gov/flood-maps/national-flood-hazard-layer"
  },
  {
    "citation_type": "rule",
    "source_id": "coa_ldc",
    "source_record_id": "25-8-261",
    "citation_url": "https://library.municode.com/TX/Austin/codes/land_development_code?nodeId=..."
  }
]
```

The agent must never assert a regulatory value (setback distance, IC limit, IFC section)
without calling a tool that returns the governing rule citation. Training-data knowledge
of codes is used only to decide which tool to call, not to provide the answer directly.

---

## Security Model

- The agent has **read-only** access to `s3://civilai-data/dev/` and the Athena
  `civilai` database via a restricted IAM role
- AWS credentials for the agent environment are separate from civil-ai-be's ETL role
- No PII is stored in session state beyond the property address
- All tool call logs are retained in CloudWatch for 90 days
