# Agent instructions for civil-ai-agent

This file is instructions for AI coding assistants (Cursor, Claude Code, etc.) working in
this repo. It exists because the real product spec already lives in `docs/` — read it,
don't skip it. This file is the compressed, load-bearing subset of that spec, kept short
enough to actually get read before you touch orchestration or add a tool.

## Read first

Before adding a tool, changing orchestration, or touching guardrails, read:

- `docs/agent-design.md` — what the agent is and is not for.
- `docs/tooling-and-orchestration.md` — the tool taxonomy and orchestration patterns.
- `docs/implementation-roadmap.md` — the phased build plan and what's actually done.

These are the design, not background reading. Code that contradicts them is a bug in the
code, not a case for updating the docs after the fact — if you think a doc is wrong,
say so and get it changed deliberately, don't just diverge silently.

## Non-negotiable rules

- Do not invent facts. If a field is missing, partial, or ambiguous, say so explicitly —
  never fill it from model memory.
- Do not infer utility capacity from service-territory/coverage data. Coverage is not
  capacity is not a will-serve commitment. Ever.
- Do not state legal conclusions, act as a permitting authority, or present output as a
  PE sign-off. The agent supports the analyst; it does not replace professional judgment.
- Web search results must be cited from an actual search result the tool returned — never
  let the model attribute a source it wasn't given. (`guardrails/finalize.py`'s source
  filtering enforces this today; don't remove or weaken it.)
- Mutating or external actions (send email, submit a form, change review state, export a
  customer-facing deliverable) require explicit user approval before executing. Never
  auto-execute these.
- High-risk behavior must be enforced in tool/service code, not prompt wording alone. A
  system-prompt instruction is not a safety control by itself.
- Saved artifacts are the system of record, not chat history. Don't build behavior that
  only works if prior turns are remembered — there is currently no cross-turn memory at
  all (see Known gaps below).

## Where we actually are — don't build ahead of this

`implementation-roadmap.md`'s own principle: data trust and evaluation coverage come
before agent polish. As of today, Phase 0 (data/contract readiness, golden eval fixtures)
and parts of Phase 1 (tested policy gates) are not done, even though some Phase 1 tools
and Phase 3 drafting logic already exist in code. Concretely:

- No golden feasibility-study eval fixtures exist yet (AGENT-012/013/014). Don't assume
  agent output quality is measured or provable — it currently isn't.
- Guardrail enforcement is off by default (`DEFAULT_GUARDRAILS.enforce = False` in
  `guardrails/shared.py`) — violations are logged, not blocked.
- Several backend fact tools have no test coverage at all.

Before adding new capability (permit checklists, external actions, multi-specialist
routing, document search), close these out first. Extending an unverified foundation
compounds the gap instead of closing it.

## Known live bugs — fix or route around, don't build on top of

1. `tools/data_client.py::resolve_parcel` sends `{"prop_id": ...}` to
   `POST /v1/entities/resolve`, but the backend's `EntityResolveRequest` model
   (`civil-ai-data/src/civilai/api/app.py`) only accepts `parcel_id` and rejects unknown
   fields. Every prop_id-based resolve call 422s today, even though the tool's own
   docstring advertises prop_id as a supported input.
2. `tools/data_client.py::get_site_by_entity` (backing the `get_site_payload` tool) calls
   `GET /v1/fe/site?entity_id=...`, which does not exist — every FE route in
   `civil-ai-data` is POST-only. This tool crashes on every call, and there is no error
   handling anywhere in the HTTP chain (`DataApiClient._request`) to catch it. Prefer
   pointing this at `GET /v1/entities/{entity_id}/facts` instead of trying to fix the FE
   route — see item 3 first.
3. `civil-ai-data`'s `GET /v1/entities/{entity_id}/facts` endpoint (the natural fit for
   multi-section agent fetches) currently applies no PII filtering, unlike its sibling
   routes. Fix that backend-side before wiring the agent to it.
4. `guardrails/prefetch_search.py`'s hardcoded `_PREFETCH_FIELD_CODES` list references
   `ZONING_DISTRICT`, which does not exist in `civil-ai-data`'s field catalog (only
   `ZONING_REGS` does) — silently dead code today, not a crash, but wrong.

## Repo-family conventions

This repo is one of five siblings under Project Landmark (`civil-ai`, `civil-ai-data`,
`civil-ai-fe`, `civil-ai-platform`, `civil-ai-agent`). `civil-ai-data` has its own
`CLAUDE.md` with the fuller engineering standards; match its spirit here: complete type
annotations, tests for anything that calls an external service (use `respx` for HTTP
mocking, no live network calls in tests), no bare `except: pass`, no speculative
abstractions or unused feature flags.
