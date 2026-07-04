# CLAUDE.md for civil-ai-agent

**Canonical file: [`AGENTS.md`](AGENTS.md).** Claude Code auto-loads `CLAUDE.md`, so this
file exists to make sure it does — but `AGENTS.md` is where the real, maintained
instructions live. Read that first. Don't duplicate its content here; if you're tempted
to add a rule, add it to `AGENTS.md`.

If you only read six lines: read `docs/agent-tuning-strategy.md` before touching
orchestration/tools/guardrails — it's the current status and roadmap, more current than
any bullet list in this repo's other docs. Branch off `develop`
(`feature/*`/`chore/*`/`fix/*`), never commit directly to `develop`/`main`. Run
`make gauntlet` before every push. Match `civil-ai-data/CLAUDE.md`'s coding standards in
spirit (complete type annotations, no bare `except: pass`, tests use `respx` and never
make live network calls). Never invent facts; never infer utility capacity from coverage
data; high-risk behavior is enforced in code, not prompt wording.
