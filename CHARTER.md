# Kando — Project Charter

## 1. Methodology
Disciplined Agentic Engineering (DAE). Every feature is born with acceptance criteria
and GWT specs before implementation. Existing features are retroactively covered via
the consolidation backlog. The ATDD pipeline (spec → IR → generated tests → passing)
is the definition of "done."

## 2. Architecture
- **Language:** Python 3.12+
- **Core runtime:** `kando/` — ledger (append-only), world (projected state),
  responders (reactive functions), budget enforcer, LLM cache, trace/lineage,
  branch/diff engine.
- **Kits:** `kits/` — domain bundles (research, diligence). Each kit is a set of
  typed responders + seed helpers. New kits follow the same pattern.
- **Entry points:** `kando` CLI (`kando/cli/main.py`); `kando-mcp` MCP server
  (`kando/mcp/server.py`).
- **LLM backend:** OpenRouter by default (OPENROUTER_API_KEY); Anthropic SDK
  fallback (ANTHROPIC_API_KEY). Model: `anthropic/claude-haiku-4-5`.
- **Optional durable backend:** KurrentDB / EventStoreDB via `esdbclient`
  (EVENTSTORE_URL env). In-memory by default.
- **Docs:** MkDocs Material, deployed to kando.ucalyptus.me via CF Pages.

## 3. Conventions
- No comments unless the WHY is non-obvious.
- No abstractions for single-use code; no speculative features.
- Touch only what the task requires — no adjacent cleanup.
- Tests live in `tests/`; acceptance tests generated into `features/NNN-slug/`.
- `.env` at repo root for secrets (gitignored); auto-loaded by the CLI.
- Commits are co-authored by Claude; pushed only on explicit request.

## 4. Scope
**In scope (current):**
- Ledger backends (memory, EventStoreDB stream)
- World projection, snapshot, branch, diff
- Responder infrastructure (base, budget, edge logic, LLM executor)
- LLM backends (OpenRouter, Anthropic)
- Kits: research, diligence (and future kits)
- CLI (`run`, `replay`, `fork`, `diff`, `trace`, `status`)
- MCP server
- Documentation (MkDocs, CF Pages)
- ATDD coverage of all the above

**Deferred (after localhost works well):**
- Managed cloud service / SaaS offering
- Multi-user auth / tenancy
- Hosted agent runs / remote execution

**Out of scope:**
- Web UI / dashboard
- Non-Python runtimes

## 5. Agent team
- **Owner:** ucalyptus (sole human decision-maker)
- **Primary agent:** Claude Code (Sonnet 4.6)
- **LLM executor model:** anthropic/claude-haiku-4-5 via OpenRouter
- **Remote agents:** dispatched via Claude Code for consolidation tasks

## 6. Quality stance
- All new features require `feature.md` + `acs.md` + `spec.md` + passing
  acceptance tests before merge.
- Mutation testing (`atdd:kill-mutants`) applied to `kando/world/`,
  `kando/ledger/`, `kando/cache/`, `kando/trace/`, `kando/branch/`.
- No broken tests on `main`.
- Coverage target: all responder logic and kit responders covered by
  generated acceptance tests.
- Docs regenerated and deployed on every push to `main`.

## 7. Autonomy stance
**Level: low-to-medium.**
The project has no staging environment or monitoring infrastructure. Agent may:
- Edit files, run tests, commit to local branches, push to `main` on request.
- Start/stop local infra (EventStoreDB via docker compose).
- Deploy docs (CF Pages, triggered by push).

Agent must ask before:
- Destructive git ops (reset --hard, force push).
- Any external API call with real cost beyond the configured LLM executor.
- Publishing / releasing packages.

Recommended upstream investment to raise autonomy ceiling: staging environment
+ basic monitoring for agent-driven validation.
