# Feature 003 — Runtime (Event Loop)

## What it is
The Runtime wires together the ledger, world projection, responders, and budget
into a single event loop. It processes seed events, fires matching responders,
and exhausts the queue — stopping when the queue is empty or the budget is hit.

## Why it matters
The Runtime is the engine of a kando run. Without it, events sit in the ledger
unprocessed. It is the integration point for every other component: ledger,
world, responders, budget enforcer, LLM cache.

## Code locations
- `kando/runtime.py` — `Runtime` class: `run()`, `replay()`, `_dispatch()`,
  `_handle_budget()`

## Existing test material
- `features/runtime.feature` — BDD scenarios (seed commit, responder firing, budget halt)
- `features/steps/runtime_steps.py` — step implementations
- `tests/test_runtime.py` — unit tests
- `tests/test_determinism.py` — determinism property tests
- `tests/test_replay.py` — replay tests
- `tests/test_crash.py` — error handling tests

## Status
- DAE coverage: ❌ feature.md ❌ acs.md ❌ spec.md ❌ acceptance tests
- Existing tests: BDD feature file + comprehensive unit tests (in flat layout)
- Next step: `/engineer.discover-acs` (reverse-engineer mode) to extract acs.md
