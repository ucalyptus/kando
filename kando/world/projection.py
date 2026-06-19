from __future__ import annotations
import copy
from typing import TYPE_CHECKING
from kando.schema import events as ev
from kando.schema.events import KandoEvent
from kando.world.graph import World, WorldObject, Relation

if TYPE_CHECKING:
    from kando.ledger.interface import LedgerStore


def project(event_stream) -> World:
    """Deterministically derive World from an ordered event stream."""
    world = World()
    for event in event_stream:
        apply(world, event)
    return world


def apply(world: World, event: KandoEvent) -> None:
    """Apply a single event to the world in-place."""
    if event.type == ev.OBJECT_CREATED:
        world.objects[event.data["id"]] = WorldObject(
            id=event.data["id"],
            type=event.data["type"],
            data=copy.deepcopy(event.data.get("data", {})),
        )
    elif event.type == ev.OBJECT_PATCHED:
        obj_id = event.data["id"]
        if obj_id not in world.objects:
            raise KeyError(f"OBJECT_PATCHED refers to unknown object: {obj_id!r}")
        world.objects[obj_id].data.update(copy.deepcopy(event.data.get("patch", {})))
    elif event.type == ev.BUDGET_EXHAUSTED:
        world.context["budget_exhausted"] = True
    elif event.type == ev.RELATION_CREATED:
        world.relations[event.data["id"]] = Relation(
            id=event.data["id"],
            type=event.data["type"],
            source_id=event.data["source_id"],
            target_id=event.data["target_id"],
            data=dict(event.data.get("data", {})),
        )
    elif event.type == ev.RELATION_REMOVED:
        world.relations.pop(event.data["id"], None)


def reproject(store: "LedgerStore") -> World:
    """Convenience: project all events from a ledger store."""
    return project(store.read_all())
