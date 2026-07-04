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
- `docs/agent-tuning-strategy.md` — the current status, bug list, and sequenced tuning
  roadmap. This is the one to check for "is X still broken" before trusting anything
  older, including the rest of this file.

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
  all (see `docs/agent-tuning-strategy.md` Phase 4 for the design to close this).

## Where we actually are — read `docs/agent-tuning-strategy.md` for the current picture

That doc (added 2026-07-04) is now the load-bearing status/roadmap doc — it supersedes
the bullet list this section used to carry, which went stale within days (see git
history if you want the record). Read it before making any tool, orchestration, or
guardrail change. Short version: the tool contract bugs are fixed (below), but the
**keystone bug is still live**: the production run path never drives structured output
(`runner.py` calls `finalize_text_output(text=message, guardrails=DEFAULT_GUARDRAILS)`
with no `structured_mode=True`), so `AgentResponse.artifacts` is always empty and the
planned eval checks have nothing structured to check. Fixing that is the single
highest-leverage next change — see the strategy doc's Phase 1.

## Known live bugs — fix or route around, don't build on top of

Two contract bugs that used to be here (`resolve_parcel` sending `prop_id` instead of
`parcel_id`; `get_site_payload` hitting a nonexistent route) were fixed in
`fix/agent-contract-bugs-f1` (merged) — tools now also return a structured
`{"status": "ok"/"error", ...}` envelope instead of raising a raw `httpx` exception.
The PII-filtering gap on `civil-ai-data`'s `GET /v1/entities/{entity_id}/facts` was
also fixed backend-side (that route now applies `_filter_entity_facts_pii`). The
`ZONING_DISTRICT` dead-code reference in `guardrails/prefetch_search.py` was removed.

Before treating any "known bug" claim in this file as current, grep the actual code —
this section has gone stale before and will again if it's trusted instead of verified.

## Repo-family conventions

This repo is one of five siblings under Project Landmark (`civil-ai`, `civil-ai-data`,
`civil-ai-fe`, `civil-ai-platform`, `civil-ai-agent`). `civil-ai-data` has its own
`CLAUDE.md` with the fuller engineering standards; match its spirit here: complete type
annotations, tests for anything that calls an external service (use `respx` for HTTP
mocking, no live network calls in tests), no bare `except: pass`, no speculative
abstractions or unused feature flags.
