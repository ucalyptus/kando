# World & Projection

## World

::: kando.world.graph.World
    options:
      show_source: true
      heading_level: 3

## WorldObject

::: kando.world.graph.WorldObject
    options:
      show_source: true
      heading_level: 3

## Relation

::: kando.world.graph.Relation
    options:
      show_source: true
      heading_level: 3

---

## Projection functions

::: kando.world.projection.project
    options:
      show_source: true
      heading_level: 3

::: kando.world.projection.apply
    options:
      show_source: true
      heading_level: 3

::: kando.world.projection.reproject
    options:
      show_source: true
      heading_level: 3

---

## Usage

```python
from kando.world.projection import project, apply, reproject
from kando.world.graph import World

# Build world from a stream of events
world = project(iter(events))

# Apply a single event incrementally
apply(world, new_event)

# Reproject directly from a LedgerStore
world = reproject(store)

# Access objects and relations
for obj in world.objects.values():
    print(obj.id, obj.type, obj.data)

for rel in world.relations.values():
    print(rel.type, rel.source_id, "→", rel.target_id)

# Runtime-level shared state (e.g., LLM cache)
cache = world.context.get("cache")
```

## Event handling

| Event type | Effect on World |
|---|---|
| `object.created` | Adds `WorldObject` to `world.objects` |
| `object.patched` | Updates `data` fields of existing object |
| `relation.created` | Adds `Relation` to `world.relations` |
| `relation.removed` | Removes relation by ID |
| All others | No-op (budget, branch, LLM, etc.) |
