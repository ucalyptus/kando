from __future__ import annotations
import json
from datetime import datetime, timezone
from pytest_bdd import scenarios, given, when, then, parsers
from kando.world.graph import World, WorldObject, Relation
from kando.world.projection import apply, project
from kando.schema.events import KandoEvent, OBJECT_CREATED, OBJECT_PATCHED, RELATION_CREATED, RELATION_REMOVED

scenarios('../world.feature')


def _ts():
    return datetime.now(timezone.utc)


def _make_created(obj_id: str, obj_type: str, data: dict) -> KandoEvent:
    return KandoEvent(
        id=f"create-{obj_id}",
        type=OBJECT_CREATED,
        source="run:test",
        actor="test",
        cause=[],
        timestamp=_ts(),
        data={"id": obj_id, "type": obj_type, "data": data},
    )


def _make_patched(obj_id: str, patch: dict) -> KandoEvent:
    return KandoEvent(
        id=f"patch-{obj_id}",
        type=OBJECT_PATCHED,
        source="run:test",
        actor="test",
        cause=[],
        timestamp=_ts(),
        data={"id": obj_id, "patch": patch},
    )


def _make_relation_created(rel_id: str, rel_type: str, src: str, tgt: str) -> KandoEvent:
    return KandoEvent(
        id=f"rel-create-{rel_id}",
        type=RELATION_CREATED,
        source="run:test",
        actor="test",
        cause=[],
        timestamp=_ts(),
        data={"id": rel_id, "type": rel_type, "source_id": src, "target_id": tgt},
    )


def _make_relation_removed(rel_id: str) -> KandoEvent:
    return KandoEvent(
        id=f"rel-remove-{rel_id}",
        type=RELATION_REMOVED,
        source="run:test",
        actor="test",
        cause=[],
        timestamp=_ts(),
        data={"id": rel_id},
    )


@given('an empty world', target_fixture='world_ctx')
def empty_world():
    return {"world": World(), "last_event": None}


@given(parsers.parse('a world with object "{obj_id}" of type "{obj_type}" with data {data_json}'),
       target_fixture='world_ctx')
def world_with_object(obj_id, obj_type, data_json):
    world = World()
    data = json.loads(data_json)
    event = _make_created(obj_id, obj_type, data)
    apply(world, event)
    return {"world": world, "last_event": event}


@given(parsers.parse('a world with relation "{rel_id}" of type "{rel_type}" between "{src}" and "{tgt}"'),
       target_fixture='world_ctx')
def world_with_relation(rel_id, rel_type, src, tgt):
    world = World()
    event = _make_relation_created(rel_id, rel_type, src, tgt)
    apply(world, event)
    return {"world": world, "last_event": event}


@given('a fixed sequence of 5 events', target_fixture='world_ctx')
def fixed_sequence():
    events = [_make_created(f"obj-{i}", "claim", {"val": i}) for i in range(5)]
    return {"world": World(), "fixed_events": events}


@when(parsers.parse('an object.created event is applied with id "{obj_id}" type "{obj_type}" data {data_json}'))
def apply_object_created(world_ctx, obj_id, obj_type, data_json):
    data = json.loads(data_json)
    event = _make_created(obj_id, obj_type, data)
    apply(world_ctx["world"], event)
    world_ctx["last_event"] = event


@when(parsers.parse('an object.patched event is applied with id "{obj_id}" patch {patch_json}'))
def apply_object_patched(world_ctx, obj_id, patch_json):
    patch = json.loads(patch_json)
    event = _make_patched(obj_id, patch)
    apply(world_ctx["world"], event)
    world_ctx["last_event"] = event


@when(parsers.parse('a relation.removed event is applied with id "{rel_id}"'))
def apply_relation_removed(world_ctx, rel_id):
    event = _make_relation_removed(rel_id)
    apply(world_ctx["world"], event)
    world_ctx["last_event"] = event


@when('I project those events 3 times')
def project_three_times(world_ctx):
    events = world_ctx["fixed_events"]
    worlds = [project(events) for _ in range(3)]
    world_ctx["projected_worlds"] = worlds


@then(parsers.parse('the world contains object "{obj_id}"'))
def check_world_has_object(world_ctx, obj_id):
    assert obj_id in world_ctx["world"].objects, f"Object {obj_id} not in world"


@then(parsers.parse('"{obj_id}" has data {data_json}'))
def check_object_data(world_ctx, obj_id, data_json):
    expected = json.loads(data_json)
    obj = world_ctx["world"].objects.get(obj_id)
    assert obj is not None, f"Object {obj_id} not found"
    assert obj.data == expected, f"Expected {expected}, got {obj.data}"


@then('the world contains no objects')
def check_no_objects(world_ctx):
    assert len(world_ctx["world"].objects) == 0, "Expected no objects in world"


@then('the world contains no relations')
def check_no_relations(world_ctx):
    assert len(world_ctx["world"].relations) == 0, "Expected no relations in world"


@then('all 3 resulting worlds are identical')
def check_worlds_identical(world_ctx):
    worlds = world_ctx["projected_worlds"]
    assert len(worlds) == 3
    first_objs = {k: v.data for k, v in worlds[0].objects.items()}
    for w in worlds[1:]:
        other_objs = {k: v.data for k, v in w.objects.items()}
        assert first_objs == other_objs, "Worlds are not identical"
