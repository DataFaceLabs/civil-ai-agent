# civil-ai-agent

AI agent that produces, explains, and validates land-development feasibility studies
for the Austin metroplex — powered by **AWS AgentCore** and the **Strands** orchestration
framework.

---

## What This Repo Does

A land-development feasibility study takes an experienced civil engineer 4–6 weeks to
complete manually. It requires querying ~20 agencies, cross-referencing regulatory codes
across city, county, state, and federal layers, and writing ~25 pages of narrative that
follows a precise professional template.

`civil-ai-agent` is the AI interface on top of that process. It:

1. **Answers questions about a parcel** — "Is this property in the Edwards Aquifer Recharge
   Zone?", "What are the impervious cover limits?", "Who is the water provider?"
2. **Generates section language** — drafts each of the 19 study sections in the ATX Civil
   professional voice, citing actual data facts pulled from the data lake
3. **Surfaces data gaps** — identifies which fields are missing for a given parcel and
   suggests where to find them (third-party API, field visit, permit lookup)
4. **Flags infeasibility signals early** — OSSF minimum lot size failure, Zone A flood
   study required, de-annexation impact on governing regulations
5. **Retrieves live regulatory content** — looks up MuniCode LDC sections, TAC rules,
   TCEQ permit status, FEMA FIRM panels when the data lake doesn't have the answer

---

## Two-Repo Architecture

```
civil-ai-be          civil-ai-agent
(data platform)      (AI interface)
     │                     │
     ▼                     ▼
 S3 + Athena  ◄────── Tool: query_section_facts()
 FastAPI /report        Tool: fetch_regulatory_text()
                        Tool: search_permit_records()
                        Tool: geocode_address()
                             │
                             ▼
                       AWS AgentCore
                       Strands Orchestrator
                             │
                             ▼
                       Section Language
                       + Citations
                       + Gap Report
```

**`civil-ai-be`** ([DataFaceLabs/civil-ai-be](https://github.com/DataFaceLabs/civil-ai-be))
owns the data platform: S3 data lake, Athena query layer, ETL overlay builders, and
the FastAPI `/report` endpoint that returns structured section facts for a given address.
See its [Data Requirements Document](https://github.com/DataFaceLabs/civil-ai-be/blob/main/docs/reference/data_requirements.md)
for the full field catalog and coverage map.

**`civil-ai-agent`** (this repo) owns the AI layer: the agent that uses those facts as
context, generates professional narrative, reasons about regulatory constraints, and
converses with the engineer/reviewer.

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Agent runtime | AWS AgentCore | Managed agent execution, session state, tool invocation |
| Orchestration | Strands | Multi-step reasoning, tool chaining, memory |
| LLM | Claude claude-sonnet-4-6 (Anthropic) | Language generation; regulatory reasoning |
| Data layer | civil-ai-be FastAPI + Athena | Section facts, citations, overlays |
| Regulatory text | MuniCode API, TAC viewer, direct URL fetch | Live code lookups |

---

## Repository Structure

```
civil-ai-agent/
├── README.md                    ← you are here
├── docs/
│   ├── architecture.md          ← AWS AgentCore + Strands system design
│   ├── atx-civil-writing-guide.md  ← ATX Civil voice, tone, regulatory style
│   ├── section-playbooks.md     ← Per-section data requirements + language patterns
│   └── data-catalog.md          ← What the data lake provides, what's missing
├── src/
│   └── (agent implementation — coming in Sprint 1)
└── tests/
    └── (coming in Sprint 1)
```

---

## Documentation Guide

Before writing a line of agent code, read these docs in order:

1. **[Architecture](docs/architecture.md)** — how the agent connects to the data lake and
   what tools it has
2. **[ATX Civil Writing Guide](docs/atx-civil-writing-guide.md)** — the professional voice
   the agent must produce; derived from analysis of 20 actual feasibility studies
3. **[Section Playbooks](docs/section-playbooks.md)** — per-section data requirements,
   boilerplate patterns, jurisdiction variations, and infeasibility flags
4. **[Data Catalog](docs/data-catalog.md)** — what's live in the data lake today vs. what
   the agent must retrieve from third-party sources

---

## Relationship to ATX Civil's Workflow

ATX Civil Engineers currently:
1. Receive a client address and project description
2. Query ~20 agencies manually (TCAD, FEMA, TCEQ, city GIS portals, utility contacts)
3. Write the report in Word using a template with `{PLACEHOLDER}` codes
4. Review and stamp

This agent targets steps 2 and 3 — the research and first-draft generation. The engineer
retains step 4 (professional judgment, PE stamp). The agent is a powerful first-draft tool,
not an autonomous document generator.

**Critical constraint:** Every factual claim in the generated report must be traceable to
a source citation (data source URL or statute reference). The agent must never assert a
regulatory value without citing the governing rule.

---

## Status

Documentation foundation: ✅ (this commit)  
Agent implementation: 🔲 (see [civil-ai-be roadmap](https://github.com/DataFaceLabs/civil-ai-be/blob/main/docs/roadmap.md))
