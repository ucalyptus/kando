# ADR-004: Budget Enforcement at the Runtime Level

**Status:** Accepted  
**Date:** 2026-06-06

## Context

Long-running agents can loop indefinitely, exhaust API budgets, or consume unbounded wall-clock time. Responders should not need to self-police — they should focus on domain logic.

## Decision

The `BudgetEnforcer` sits inside `Runtime` and checks four limits after every event:

- `max_events`: total events appended to the ledger
- `max_llm_cost_usd`: cumulative cost tracked by summing `cost_usd` from `llm.response` events
- `max_seconds`: wall-clock elapsed since the run started
- `max_depth`: maximum causal depth (longest chain of `cause` edges)

When any limit is breached, the runtime emits a `BUDGET_EXHAUSTED` event, appends it to the ledger, applies it to the world (setting `world.context["budget_exhausted"] = True`), and halts the event loop. No responder is called after exhaustion.

## Consequences

**Positive:**
- Responders are never responsible for their own termination.
- Budget exhaustion is auditable: the `BUDGET_EXHAUSTED` event is in the ledger with the reason and current counters.
- Callers can inspect `world.context.get("budget_exhausted")` to determine if a run completed normally or was truncated.
- LLM cost tracking is automatic: any responder that emits `llm.response` with `cost_usd` contributes to the budget.

**Negative:**
- Budget check is per-event, not per-token or per-wall-clock-tick. A single slow LLM call that takes 5 minutes is not interrupted mid-call — the budget is checked when it returns.
- The `max_llm_cost_usd` limit only works if executors faithfully emit `llm.response` with accurate `cost_usd`. A rogue responder that makes direct LLM calls without emitting events bypasses cost tracking.

## Defaults

`Budget()` defaults: `max_events=1000`, `max_llm_cost_usd=10.0`, `max_seconds=300`, `max_depth=50`. All are overridable at `Runtime` construction time.
