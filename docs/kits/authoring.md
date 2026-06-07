# Writing a Kit

A kit is a Python module with two exported functions:

```python
def create_kit() -> list[Responder]: ...
def seed_from_goal(goal: str, run_id: str) -> list[KandoEvent]: ...  # optional
```

## Minimal kit

```python
# kits/planning/kit.py
from __future__ import annotations
from typing import Iterator
from kando.responders.base import Responder
from kando.schema.events import KandoEvent, OBJECT_CREATED, make_event
from kando.world.graph import World

TASK = "Task"
SUBTASK = "Subtask"

_COUNTER = 0

def _on_task_created(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
    if event.data.get("type") != TASK:
        return
    global _COUNTER
    _COUNTER += 1
    task_id = event.data["id"]
    yield make_event(
        type=OBJECT_CREATED,
        source=event.source,
        actor="planning.decomposer",
        cause=[event.id],
        data={"id": f"subtask-{_COUNTER}", "type": SUBTASK,
              "data": {"text": "Step 1", "parent": task_id}},
    )

def create_kit() -> list[Responder]:
    return [
        Responder(
            name="planning.on_task_created",
            pattern=frozenset({OBJECT_CREATED}),
            fn=_on_task_created,
        ),
    ]
```

## Best practices

### Use domain-typed object data

```python
# Good: typed data dict
{"id": "task-001", "type": "Task", "data": {"title": "Research", "priority": 1}}

# Avoid: loose untyped fields at top level
{"task_title": "Research", "priority": 1}
```

### Guard on object type in every responder

Responders receive ALL `object.created` events. Always check `event.data.get("type")` first:

```python
def _on_company_created(event: KandoEvent, world: World):
    if event.data.get("type") != "Company":
        return   # ← this is critical
    ...
```

### Use `world.objects` for lookups, not event data

After the event fires, the object is already applied to the world. Reference it from `world.objects` when you need other objects' data:

```python
claim_id = event.data["data"]["claim_id"]
claim_obj = world.objects.get(claim_id)
if not claim_obj:
    return  # guard against events that arrive before their parents
```

### Access the LLM cache from `world.context`

```python
def _llm_responder(event: KandoEvent, world: World):
    cache = world.context.get("cache")  # LLMCache or None
    if cache:
        cached = cache.get({"model": "x", "prompt": "..."})
        if cached:
            # serve from cache
```

### `_COUNTER` for ID generation

Use a module-level counter for stable, monotonic IDs. Reset it in tests if needed.

## Seed events

```python
from datetime import datetime, timezone
from kando.schema.events import KandoEvent, OBJECT_CREATED

def seed_from_goal(goal: str, run_id: str) -> list[KandoEvent]:
    return [KandoEvent(
        id=f"task.created-{run_id[:8]}",
        type=OBJECT_CREATED,
        source=f"run:{run_id}",
        actor="cli",
        cause=[],                          # root event — no cause
        timestamp=datetime.now(timezone.utc),
        data={"id": f"task-{run_id[:8]}", "type": "Task",
              "data": {"title": goal}},
    )]
```

## Edge logic

Register logic that fires automatically when a relation of a given type is created:

```python
from kando.responders.edge import edge_logic
from kando.schema.events import KandoEvent, OBJECT_CREATED, make_event
from kando.world.graph import World

@edge_logic("blocks")
def on_blocks(event: KandoEvent, world: World):
    """When a 'blocks' relation is created, pause the blocked task."""
    blocked_id = event.data.get("target_id")
    if blocked_id and blocked_id in world.objects:
        yield make_event(
            type=OBJECT_CREATED, source=event.source,
            actor="edge.blocks", cause=[event.id],
            data={"id": f"pause-{blocked_id}", "type": "PauseSignal",
                  "data": {"task_id": blocked_id}},
            run_id_counter=0,
        )
```

## Testing a kit

```python
from kando.ledger.memory import MemoryLedgerStore
from kando.runtime import Runtime
from kits.planning.kit import create_kit, seed_from_goal, TASK, SUBTASK

def test_task_creates_subtask():
    store = MemoryLedgerStore("test-run")
    seed = seed_from_goal("Build feature X", "testrun001")
    world = Runtime(ledger=store, responders=create_kit()).run(seed)
    subtasks = [o for o in world.objects.values() if o.type == SUBTASK]
    assert len(subtasks) == 1
    assert subtasks[0].data["parent"] == f"task-testrun0"
```

## Delivery integration

```python
from kando.responders.delivery import DeliveryBus, create_delivery_responder

bus = DeliveryBus()
bus.subscribe(print, name="logger")                         # log all events
bus.subscribe(webhook_fn, name="webhook",
              pattern={"budget.exhausted", "object.created"})

runtime = Runtime(
    ledger=store,
    responders=[*create_kit(), create_delivery_responder(bus)],
)
```
