# Ledger

The ledger is the append-only event log for a single agent run.

## LedgerStore (interface)

::: kando.ledger.interface.LedgerStore
    options:
      show_source: true
      heading_level: 3

---

## MemoryLedgerStore

In-process ledger for testing and exploration. No persistence.

::: kando.ledger.memory.MemoryLedgerStore
    options:
      show_source: true
      heading_level: 3

```python
from kando.ledger.memory import MemoryLedgerStore

store = MemoryLedgerStore("my-run")
store.append([event1, event2])
all_events = list(store.read_all())
```

---

## EventStreamLedgerStore

Durable ledger backed by EventStoreDB.

::: kando.ledger.stream.EventStreamLedgerStore
    options:
      show_source: true
      heading_level: 3

```python
import os
os.environ["EVENTSTORE_URL"] = "http://localhost:2113"

from kando.ledger.stream import EventStreamLedgerStore

store = EventStreamLedgerStore("my-run-001")
store.append([event])
for e in store.read(from_position=0):
    print(e.id, e.type)
```

!!! note "Requires EventStoreDB"
    Install with `pip install -e ".[stream]"` and start EventStoreDB with:
    ```bash
    docker compose up -d eventstore
    export EVENTSTORE_URL=http://localhost:2113
    ```

---

## Snapshot

World checkpoints: fast startup without replaying the full ledger.

```python
from kando.world.snapshot import save_snapshot, load_snapshot

# Save a checkpoint after processing N events
save_snapshot(run_id="my-run", world=world, position=100)

# Load on next startup — fall back to full replay if absent
result = load_snapshot("my-run")
if result:
    world, position = result
    # replay only events after `position`
else:
    world = reproject(store)
```

Set `KANDO_SNAPSHOT_DIR` to control where snapshots are stored (default: `.kando_snapshots`).
