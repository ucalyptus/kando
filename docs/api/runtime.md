# Runtime

::: kando.runtime.Runtime
    options:
      show_source: true
      heading_level: 2

---

## Usage

```python
from kando.runtime import Runtime
from kando.ledger.memory import MemoryLedgerStore
from kando.responders.budget import Budget
from kando.cache.llm import LLMCache
from kits.diligence.kit import create_kit, seed_from_goal

run_id = "my-run-001"
store = MemoryLedgerStore(run_id)
cache = LLMCache()

runtime = Runtime(
    ledger=store,
    responders=create_kit(),
    budget=Budget(max_events=500, max_wall_seconds=60.0),
    cache=cache,
)

seed = seed_from_goal("Evaluate Stripe", run_id)
world = runtime.run(seed)

# World is also accessible via load() at any time
world2 = runtime.load()
```

## Strict replay

```python
# Permissive replay: reproject the ledger (fast, no re-firing)
world = runtime.replay(strict=False)

# Strict replay: re-execute seed events through responders
world = runtime.replay(strict=True)
```

Strict replay is useful for verifying that your responders are deterministic. If the strict world diverges from the permissive world, you have non-deterministic responders.
