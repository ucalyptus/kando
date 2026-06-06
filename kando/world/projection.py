from __future__ import annotations
from kando.schema import events as ev
from kando.schema.events import KandoEvent
from kando.world.graph import World, WorldObject, Relation


def project(event_stream) -> World:
    """Deterministically derive World from an ordered event stream."""
    world = World()
    for event in event_stream:
        apply(world, event)
    return world


def apply(world: World, event: KandoEvent) -> None:
    match event.type:
        case ev.OBJECT_CREATED:
            world.objects[event.data["id"]] = WorldObject(
                id=event.data["id"],
                type=event.data["type"],
                data=event.data.get("data", {}),
            )
        case ev.OBJECT_PATCHED:
            obj = world.objects.get(event.data["id"])
            if obj:
                obj.data.update(event.data.get("patch", {}))
        case ev.RELATION_CREATED:
            world.relations[event.data["id"]] = Relation(
                id=event.data["id"],
                type=event.data["type"],
                source_id=event.data["source_id"],
                target_id=event.data["target_id"],
                data=event.data.get("data", {}),
            )
        case ev.RELATION_REMOVED:
            world.relations.pop(event.data["id"], None)
