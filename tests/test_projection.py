"""Targeted unit tests for kando.world.projection — mutation hardening."""
from __future__ import annotations
from datetime import datetime, timezone

from kando.schema.events import KandoEvent, OBJECT_CREATED, OBJECT_PATCHED
from kando.world.graph import World, WorldObject
from kando.world.projection import apply


def _ts():
    return datetime.now(timezone.utc)


def _created(obj_id: str, data: dict) -> KandoEvent:
    return KandoEvent(
        id=f"e-{obj_id}", type=OBJECT_CREATED,
        source="test", actor="test", cause=[], timestamp=_ts(),
        data={"id": obj_id, "type": "claim", "data": data},
    )


def _patched(obj_id: str, patch: dict) -> KandoEvent:
    return KandoEvent(
        id=f"p-{obj_id}", type=OBJECT_PATCHED,
        source="test", actor="test", cause=[], timestamp=_ts(),
        data={"id": obj_id, "patch": patch},
    )


def test_object_data_is_deep_copied_on_apply():
    # Mutating a nested value inside the event dict after apply must not
    # change the world — only deepcopy gives this guarantee (not copy.copy).
    nested = {"inner": {"v": 1}}
    event = _created("obj-1", nested)
    world = World()
    apply(world, event)

    # Mutate the nested dict that the event still references
    event.data["data"]["inner"]["v"] = 999

    assert world.objects["obj-1"].data["inner"]["v"] == 1


def test_patch_data_is_deep_copied_on_apply():
    # Same isolation guarantee for object.patched events.
    world = World()
    world.objects["obj-1"] = WorldObject(id="obj-1", type="t", data={})
    nested_patch = {"nested": {"v": 1}}
    event = _patched("obj-1", nested_patch)
    apply(world, event)

    # Mutate the nested dict that the event still references
    event.data["patch"]["nested"]["v"] = 999

    assert world.objects["obj-1"].data["nested"]["v"] == 1
