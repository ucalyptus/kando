# Budget

Budget enforcement applies resource limits to every run. When any limit is hit, a `budget.exhausted` event is written to the ledger and the run stops.

## Budget

::: kando.responders.budget.Budget
    options:
      show_source: true
      heading_level: 3

## BudgetEnforcer

::: kando.responders.budget.BudgetEnforcer
    options:
      show_source: true
      heading_level: 3

---

## Limits

| Limit | Default | Description |
|---|---|---|
| `max_events` | 10,000 | Maximum total events in the run |
| `max_llm_cost_usd` | $10.00 | Maximum LLM spend (accumulated from `llm.response` events with `cost_usd`) |
| `max_wall_seconds` | 3,600 | Maximum wall-clock time (1 hour) |
| `max_recursion_depth` | 50 | Maximum causal depth: how many responder hops from the seed |

## Usage

```python
from kando.responders.budget import Budget
from kando.runtime import Runtime

# Tight limits for a fast smoke test
runtime = Runtime(
    ledger=store,
    responders=create_kit(),
    budget=Budget(
        max_events=100,
        max_llm_cost_usd=0.50,
        max_wall_seconds=30.0,
        max_recursion_depth=10,
    ),
)
world = runtime.run(seed)

# Check if budget was exhausted
from kando.schema.events import BUDGET_EXHAUSTED
all_events = list(store.read_all())
exhausted = [e for e in all_events if e.type == BUDGET_EXHAUSTED]
if exhausted:
    reasons = exhausted[0].data["reasons"]
    print("Budget exhausted:", reasons)
```

## The `budget.exhausted` event

When a limit is hit, the enforcer emits:

```python
KandoEvent(
    type="budget.exhausted",
    data={
        "reasons": ["max_events=10000"],  # list of triggered limits
        "event_count": 10001,
        "llm_cost_usd": 2.50,
        "elapsed_seconds": 42.1,
        "depth": 7,
    }
)
```

Multiple limits can be reported in a single `reasons` list.

## Recursion depth

Depth is tracked via the causal chain: `depth[event] = max(depth[cause] for cause in event.cause) + 1`. Root events (no cause) have depth 0. This makes infinite responder chains impossible.
