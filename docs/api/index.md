# API Reference

Complete API reference for the `kando` Python package.

## Quick links

| Module | Key classes / functions |
|---|---|
| [Runtime](runtime.md) | `Runtime` — main event loop |
| [Ledger](ledger.md) | `LedgerStore`, `MemoryLedgerStore`, `EventStreamLedgerStore` |
| [World & Projection](world.md) | `World`, `WorldObject`, `Relation`, `project()`, `apply()`, `reproject()` |
| [Budget](budget.md) | `Budget`, `BudgetEnforcer` |
| [Delivery Bus](delivery.md) | `DeliveryBus`, `create_delivery_responder()` |
| [LLM Cache](cache.md) | `LLMCache`, `ScopedLLMCache` |
| [Trace & Lineage](trace.md) | `build_lineage_index()`, `explain()` |
| [Branch & Diff](branch.md) | `BranchMeta`, `fork()`, `WorldDiff`, `diff()` |
| [LLM Executor](llm_executor.md) | `LLMExecutorResponder`, `LLMFn` |

## Installation

```bash
pip install -e .              # core (no extras)
pip install -e ".[stream]"    # + EventStoreDB backend
pip install -e ".[mcp]"       # + MCP server
pip install -e ".[dev]"       # + test tools
```

## Importing

```python
from kando.runtime import Runtime
from kando.ledger.memory import MemoryLedgerStore
from kando.ledger.stream import EventStreamLedgerStore
from kando.world.graph import World, WorldObject, Relation
from kando.world.projection import project, apply, reproject
from kando.world.snapshot import save_snapshot, load_snapshot
from kando.responders.base import Responder
from kando.responders.budget import Budget, BudgetEnforcer
from kando.responders.delivery import DeliveryBus, create_delivery_responder
from kando.responders.edge import edge_logic
from kando.cache.llm import LLMCache, ScopedLLMCache
from kando.trace.lineage import build_lineage_index, explain
from kando.branch.diff import diff, WorldDiff
from kando.branch.fork import BranchMeta, fork
from kando.schema.events import KandoEvent, OBJECT_CREATED, RELATION_CREATED, make_event
```
