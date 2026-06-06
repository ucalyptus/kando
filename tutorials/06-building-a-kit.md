# Tutorial 6 — Building a Kit

**BLUF: A kit is a directory with a `kit.py` that exports `create_kit()`
(returns responders) and optionally `seed_from_goal()` (turns a
natural-language goal into seed events). That's the entire contract.**

---

## Why this matters

Kando has no opinion about what a "task," "belief," or "claim" is — that's
domain vocabulary defined by **your kit**. The runtime only knows events.
A kit packages your domain types, responders, and seed logic into a
reusable bundle.

---

## The kit contract

A kit module must export:

```python
def create_kit() -> list[Responder]:
    """Return all responders for this domain."""
    ...
```

And optionally:

```python
def seed_from_goal(goal: str, run_id: str) -> list[KandoEvent]:
    """Turn a free-text goal into seed events."""
    ...
```

If `seed_from_goal` is missing, the CLI creates a generic `Goal` object.

---

## Step-by-step: build a "planning" kit

### 1. Create the directory

```bash
mkdir -p kits/planning
touch kits/planning/__init__.py
```

### 2. Define domain types

In `kits/planning/kit.py`:

```python
"""Planning kit: decompose a goal into milestones and tasks."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Iterator

from kando.responders.base import Responder
from kando.schema.events import (
    KandoEvent, OBJECT_CREATED, RELATION_CREATED, make_event,
)
from kando.world.graph import World

# Object types
PLAN      = "Plan"
MILESTONE = "Milestone"
TASK      = "Task"

# Relation types
CONTAINS = "contains"  # Plan -> Milestone, Milestone -> Task
```

### 3. Write responders

```python
def _on_plan_created(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
    """When a Plan is created, decompose it into milestones."""
    if event.data.get("type") != PLAN:
        return

    plan_id = event.data["id"]
    plan_text = event.data.get("data", {}).get("text", plan_id)

    for i, phase in enumerate(["Research", "Prototype", "Ship"], 1):
        m_id = f"milestone-{uuid.uuid4().hex[:8]}"
        m_event = make_event(
            type=OBJECT_CREATED,
            source=event.source,
            actor="planning.on_plan_created",
            cause=[event.id],
            data={
                "id": m_id,
                "type": MILESTONE,
                "data": {"text": f"{phase}: {plan_text}", "order": i},
            },
        )
        yield m_event

        yield make_event(
            type=RELATION_CREATED,
            source=event.source,
            actor="planning.on_plan_created",
            cause=[m_event.id],
            data={
                "id": f"rel-contains-{uuid.uuid4().hex[:8]}",
                "type": CONTAINS,
                "source_id": plan_id,
                "target_id": m_id,
            },
        )


def _on_milestone_created(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
    """When a Milestone is created, create a placeholder Task for it."""
    if event.data.get("type") != MILESTONE:
        return

    m_id = event.data["id"]
    m_text = event.data.get("data", {}).get("text", m_id)
    t_id = f"task-{uuid.uuid4().hex[:8]}"

    t_event = make_event(
        type=OBJECT_CREATED,
        source=event.source,
        actor="planning.on_milestone_created",
        cause=[event.id],
        data={
            "id": t_id,
            "type": TASK,
            "data": {"text": f"Execute: {m_text}", "status": "pending"},
        },
    )
    yield t_event

    yield make_event(
        type=RELATION_CREATED,
        source=event.source,
        actor="planning.on_milestone_created",
        cause=[t_event.id],
        data={
            "id": f"rel-contains-{uuid.uuid4().hex[:8]}",
            "type": CONTAINS,
            "source_id": m_id,
            "target_id": t_id,
        },
    )
```

### 4. Export the kit

```python
def seed_from_goal(goal: str, run_id: str) -> list[KandoEvent]:
    plan_id = f"plan-{run_id[:8]}"
    return [
        KandoEvent(
            id=f"plan.created-{run_id[:8]}",
            type=OBJECT_CREATED,
            source=f"run:{run_id}",
            actor="cli",
            cause=[],
            timestamp=datetime.now(timezone.utc),
            data={"id": plan_id, "type": PLAN, "data": {"text": goal}},
        )
    ]


def create_kit() -> list[Responder]:
    return [
        Responder(
            name="planning.on_plan_created",
            pattern=frozenset({OBJECT_CREATED}),
            fn=_on_plan_created,
        ),
        Responder(
            name="planning.on_milestone_created",
            pattern=frozenset({OBJECT_CREATED}),
            fn=_on_milestone_created,
        ),
    ]
```

### 5. Run it

```bash
.venv/bin/python -m kando.cli.main run kits/planning --goal "Launch v2"
```

Expected output: a Plan with three Milestones, each containing a Task,
all connected by `contains` relations. Every object traces back to the
seed "Launch v2" goal.

---

## Kit design principles

| Principle | Explanation |
|---|---|
| **Responders don't call each other** | They communicate through events only |
| **Domain types are just strings** | `"Plan"`, `"Milestone"` — the runtime doesn't validate them |
| **Seed events set the initial conditions** | Everything else is reactive |
| **Keep responders small** | One responsibility per responder; chains handle complexity |

---

## Key takeaways

- A kit is a `kit.py` with `create_kit()` and optionally `seed_from_goal()`.
- Define domain types as string constants — the runtime only sees events.
- Responders compose into chains without knowing about each other.
- Run any kit with `kando run kits/<name> --goal "..."`.

---

**Next:** [Tutorial 7 — MCP Integration](07-mcp-integration.md)
