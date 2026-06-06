"""Step definitions for features/001-world/spec.md.

Complements world_steps.py (existing steps reused here via shared fixtures).
Only NEW steps are defined in this file; existing step phrases are inherited.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone

from pytest_bdd import scenarios, given, when, then, parsers

from kando.ledger.memory import MemoryLedgerStore
from kando.schema.events import (
    KandoEvent,
    OBJECT_CREATED,
    OBJECT_PATCHED,
    RELATION_CREATED,
    RELATION_REMOVED,
    BUDGET_EXHAUSTED,
)
from kando.world.graph import World, Relation
from kando.world.projection import apply, project, reproject
from kando.world.snapshot import load_snapshot, save_snapshot

scenarios("../001-world/spec.md")


# ─── shared steps (re-declared here because pytest-bdd 8.x uses per-module
#     step registries — steps defined in world_steps.py are not visible in
#     world_spec_steps.py's test functions even in the same pytest session) ────

@given("an empty world", target_fixture="world_ctx")
def _empty_world():
    return {"world": World(), "last_event": None}


@given(parsers.parse('a world with object "{obj_id}" of type "{obj_type}" with data {data_json}'), target_fixture="world_ctx")
def _world_with_object(obj_id, obj_type, data_json):
    world = World()
    data = json.loads(data_json)
    event = KandoEvent(
        id=f"create-{obj_id}", type=OBJECT_CREATED, source="run:spec",
        actor="spec", cause=[], timestamp=datetime.now(timezone.utc),
        data={"id": obj_id, "type": obj_type, "data": data},
    )
    apply(world, event)
    return {"world": world, "last_event": event}


@given(parsers.parse('a world with relation "{rel_id}" of type "{rel_type}" between "{src}" and "{tgt}"'), target_fixture="world_ctx")
def _world_with_relation(rel_id, rel_type, src, tgt):
    world = World()
    event = KandoEvent(
        id=f"rel-{rel_id}", type=RELATION_CREATED, source="run:spec",
        actor="spec", cause=[], timestamp=datetime.now(timezone.utc),
        data={"id": rel_id, "type": rel_type, "source_id": src, "target_id": tgt},
    )
    apply(world, event)
    return {"world": world, "last_event": event}


@given("a fixed sequence of 5 events", target_fixture="world_ctx")
def _fixed_sequence():
    events = [
        KandoEvent(id=f"create-obj-{i}", type=OBJECT_CREATED, source="run:spec",
                   actor="spec", cause=[], timestamp=datetime.now(timezone.utc),
                   data={"id": f"obj-{i}", "type": "claim", "data": {"val": i}})
        for i in range(5)
    ]
    return {"world": World(), "fixed_events": events}


@when(parsers.parse('an object.created event is applied with id "{obj_id}" type "{obj_type}" data {data_json}'))
def _apply_object_created(world_ctx, obj_id, obj_type, data_json):
    data = json.loads(data_json)
    event = KandoEvent(
        id=f"create-{obj_id}", type=OBJECT_CREATED, source="run:spec",
        actor="spec", cause=[], timestamp=datetime.now(timezone.utc),
        data={"id": obj_id, "type": obj_type, "data": data},
    )
    apply(world_ctx["world"], event)
    world_ctx["last_event"] = event


@when(parsers.parse('an object.patched event is applied with id "{obj_id}" patch {patch_json}'))
def _apply_object_patched(world_ctx, obj_id, patch_json):
    patch = json.loads(patch_json)
    event = KandoEvent(
        id=f"patch-{obj_id}", type=OBJECT_PATCHED, source="run:spec",
        actor="spec", cause=[], timestamp=datetime.now(timezone.utc),
        data={"id": obj_id, "patch": patch},
    )
    apply(world_ctx["world"], event)
    world_ctx["last_event"] = event


@when(parsers.parse('a relation.removed event is applied with id "{rel_id}"'))
def _apply_relation_removed(world_ctx, rel_id):
    event = KandoEvent(
        id=f"rel-remove-{rel_id}", type=RELATION_REMOVED, source="run:spec",
        actor="spec", cause=[], timestamp=datetime.now(timezone.utc),
        data={"id": rel_id},
    )
    apply(world_ctx["world"], event)
    world_ctx["last_event"] = event


@when("I project those events 3 times")
def _project_three_times(world_ctx):
    events = world_ctx["fixed_events"]
    world_ctx["projected_worlds"] = [project(events) for _ in range(3)]


@then(parsers.parse('the world contains object "{obj_id}"'))
def _check_world_has_object(world_ctx, obj_id):
    assert obj_id in world_ctx["world"].objects, f"Object {obj_id!r} not in world"


@then(parsers.parse('"{obj_id}" has data {data_json}'))
def _check_object_data(world_ctx, obj_id, data_json):
    expected = json.loads(data_json)
    obj = world_ctx["world"].objects.get(obj_id)
    assert obj is not None, f"Object {obj_id!r} not found"
    assert obj.data == expected, f"Expected {expected}, got {obj.data}"


@then("the world contains no objects")
def _check_no_objects(world_ctx):
    assert len(world_ctx["world"].objects) == 0


@then("the world contains no relations")
def _check_no_relations(world_ctx):
    assert len(world_ctx["world"].relations) == 0


@then("all 3 resulting worlds are identical")
def _check_worlds_identical(world_ctx):
    worlds = world_ctx["projected_worlds"]
    first = {k: v.data for k, v in worlds[0].objects.items()}
    for w in worlds[1:]:
        other = {k: v.data for k, v in w.objects.items()}
        assert first == other


# ─── helpers ─────────────────────────────────────────────────────────────────


def _ts():
    return datetime.now(timezone.utc)


def _created(obj_id, obj_type, data=None):
    payload = {"id": obj_id, "type": obj_type}
    if data is not None:
        payload["data"] = data
    return KandoEvent(
        id=f"create-{obj_id}", type=OBJECT_CREATED, source="run:spec",
        actor="spec", cause=[], timestamp=_ts(), data=payload,
    )


def _rel_created(rel_id, rel_type, src, tgt, data=None):
    payload = {"id": rel_id, "type": rel_type, "source_id": src, "target_id": tgt}
    if data is not None:
        payload["data"] = data
    return KandoEvent(
        id=f"rel-{rel_id}", type=RELATION_CREATED, source="run:spec",
        actor="spec", cause=[], timestamp=_ts(), data=payload,
    )


def _setup_snap_dir(world_ctx, monkeypatch, tmp_path):
    import kando.world.snapshot as snap
    if "snap_dir" not in world_ctx:
        snap_dir = tmp_path / "snapshots"
        world_ctx["snap_dir"] = snap_dir
        monkeypatch.setenv("KANDO_SNAPSHOT_DIR", str(snap_dir))
    snap._SNAPSHOT_DIR = world_ctx["snap_dir"]


# ─── given ───────────────────────────────────────────────────────────────────

@given(parsers.parse('relation "{rel_id}" of type "{rel_type}" between "{src}" and "{tgt}" is also in the world'))
def add_relation_to_world(world_ctx, rel_id, rel_type, src, tgt):
    """Add a relation to the existing world without replacing world_ctx."""
    apply(world_ctx["world"], _rel_created(rel_id, rel_type, src, tgt))


@given(parsers.parse('a ledger store containing events that created "{obj_a}" of type "{type_a}" and "{obj_b}" of type "{type_b}"'), target_fixture='world_ctx')
def ledger_with_two_objects(obj_a, type_a, obj_b, type_b):
    store = MemoryLedgerStore("spec-test")
    store.append([_created(obj_a, type_a, {}), _created(obj_b, type_b, {})])
    return {"world": World(), "store": store}


@given('the snapshot directory is set to a custom path via KANDO_SNAPSHOT_DIR', target_fixture='world_ctx')
def set_custom_snapshot_dir(monkeypatch, tmp_path):
    import kando.world.snapshot as snap
    snap_dir = tmp_path / "custom_snaps"
    monkeypatch.setenv("KANDO_SNAPSHOT_DIR", str(snap_dir))
    snap._SNAPSHOT_DIR = snap_dir
    return {"world": World(), "snap_dir": snap_dir}


@given('the snapshot directory does not exist', target_fixture='world_ctx')
def snap_dir_absent(monkeypatch, tmp_path):
    import kando.world.snapshot as snap
    snap_dir = tmp_path / "absent_snaps"
    monkeypatch.setenv("KANDO_SNAPSHOT_DIR", str(snap_dir))
    snap._SNAPSHOT_DIR = snap_dir
    assert not snap_dir.exists()
    return {"world": World(), "snap_dir": snap_dir}


@given(parsers.parse('a snapshot file exists for run "{run_id}" but contains malformed JSON'), target_fixture='world_ctx')
def corrupt_snapshot_file(run_id, monkeypatch, tmp_path):
    import kando.world.snapshot as snap
    snap_dir = tmp_path / "corrupt_snaps"
    snap_dir.mkdir(parents=True)
    monkeypatch.setenv("KANDO_SNAPSHOT_DIR", str(snap_dir))
    snap._SNAPSHOT_DIR = snap_dir
    (snap_dir / f"{run_id}.json").write_text("{ not valid json }{{{")
    return {"world": World(), "snap_dir": snap_dir}


@given(parsers.parse('an object.created event payload for id "{obj_id}" type "{obj_type}" data {data_json}'), target_fixture='event_payload_ctx')
def event_payload(obj_id, obj_type, data_json):
    return {"obj_id": obj_id, "event": _created(obj_id, obj_type, json.loads(data_json))}


# ─── when ────────────────────────────────────────────────────────────────────

@when(parsers.parse('a relation.created event is applied with id "{rel_id}" type "{rel_type}" from "{src}" to "{tgt}"'))
def apply_relation_created(world_ctx, rel_id, rel_type, src, tgt):
    apply(world_ctx["world"], _rel_created(rel_id, rel_type, src, tgt))


@when(parsers.parse('a relation.created event is applied with id "{rel_id}" type "{rel_type}" from "{src}" to "{tgt}" and no data field'))
def apply_relation_created_no_data(world_ctx, rel_id, rel_type, src, tgt):
    apply(world_ctx["world"], _rel_created(rel_id, rel_type, src, tgt))  # no data= → no "data" key


@when('a budget.exhausted event is applied')
def apply_budget_exhausted(world_ctx):
    event = KandoEvent(
        id="budget-exhausted", type=BUDGET_EXHAUSTED, source="run:spec",
        actor="spec", cause=[], timestamp=_ts(), data={},
    )
    apply(world_ctx["world"], event)


@when(parsers.re(r'I project a stream that creates "(?P<obj_a>[^"]+)" of type "(?P<type_a>[^"]+)" then "(?P<obj_b>[^"]+)" of type "(?P<type_b>[^"]+)" then a "(?P<rel_type>[^"]+)" relation from "(?P<rel_src>[^"]+)" to "(?P<rel_tgt>[^"]+)"'))
def project_custom_stream(world_ctx, obj_a, type_a, obj_b, type_b, rel_type, rel_src, rel_tgt):
    events = [
        _created(obj_a, type_a, {}),
        _created(obj_b, type_b, {}),
        _rel_created("stream-rel", rel_type, rel_src, rel_tgt),
    ]
    world_ctx["world"] = project(events)
    world_ctx.update({"_rel_type": rel_type, "_rel_src": rel_src, "_rel_tgt": rel_tgt})


@when('I project an empty event stream')
def project_empty(world_ctx):
    world_ctx["world"] = project([])


@when('I reproject from the ledger store')
def do_reproject(world_ctx):
    world_ctx["world"] = reproject(world_ctx["store"])


@when(parsers.parse('I look up object "{obj_id}"'), target_fixture='lookup_result')
def lookup_object(world_ctx, obj_id):
    return world_ctx["world"].get_object(obj_id)


@when(parsers.parse('I look up relations for object "{obj_id}"'), target_fixture='lookup_rels')
def lookup_relations(world_ctx, obj_id):
    return world_ctx["world"].get_relations(obj_id)


@when(parsers.parse('I look up relations for object "{obj_id}" of type "{rel_type}"'), target_fixture='lookup_rels')
def lookup_relations_typed(world_ctx, obj_id, rel_type):
    return world_ctx["world"].get_relations(obj_id, rel_type)


@when(parsers.parse('I save the world as run "{run_id}" at ledger position {position:d}'))
def save_world_snapshot(world_ctx, run_id, position, monkeypatch, tmp_path):
    _setup_snap_dir(world_ctx, monkeypatch, tmp_path)
    save_snapshot(run_id, world_ctx["world"], position)


@when(parsers.parse('I reload the snapshot for run "{run_id}"'), target_fixture='snap_result')
def reload_snapshot(run_id, world_ctx, monkeypatch, tmp_path):
    _setup_snap_dir(world_ctx, monkeypatch, tmp_path)
    return load_snapshot(run_id)


@when(parsers.parse('the world is replaced by one containing object "{obj_id}" of type "{obj_type}" with data {data_json}'))
def replace_world(world_ctx, obj_id, obj_type, data_json):
    new_world = World()
    apply(new_world, _created(obj_id, obj_type, json.loads(data_json)))
    world_ctx["world"] = new_world


@when(parsers.parse('I project 5 distinct object-creation events in forward order'), target_fixture='order_ctx')
def project_5_forward():
    events = [_created(f"obj-{i}", "claim", {"val": i}) for i in range(5)]
    return {"events": events, "forward": project(events), "reverse": None}


@when('I project the same 5 events in reverse order')
def project_5_reverse(order_ctx):
    order_ctx["reverse"] = project(list(reversed(order_ctx["events"])))


@when(parsers.parse('I apply that event then mutate the event data to {data_json}'))
def apply_then_mutate(world_ctx, event_payload_ctx, data_json):
    event = event_payload_ctx["event"]
    apply(world_ctx["world"], event)
    event.data["data"] = json.loads(data_json)


@when(parsers.parse('an object.created event is applied with id "{obj_id}" type "{obj_type}" and no data field'))
def apply_created_no_data(world_ctx, obj_id, obj_type):
    event = KandoEvent(
        id=f"create-{obj_id}", type=OBJECT_CREATED, source="run:spec",
        actor="spec", cause=[], timestamp=_ts(), data={"id": obj_id, "type": obj_type},
    )
    apply(world_ctx["world"], event)


@when(parsers.parse('an event of type "{event_type}" is applied'))
def apply_generic_event(world_ctx, event_type):
    event = KandoEvent(
        id=f"evt-{event_type}", type=event_type, source="run:spec",
        actor="spec", cause=[], timestamp=_ts(), data={},
    )
    apply(world_ctx["world"], event)


# ─── then ────────────────────────────────────────────────────────────────────

@then(parsers.parse('the world contains relation "{rel_id}" of type "{rel_type}" from "{src}" to "{tgt}"'))
def check_relation_full(world_ctx, rel_id, rel_type, src, tgt):
    rel = world_ctx["world"].relations.get(rel_id)
    assert rel is not None, f"Relation {rel_id!r} not in world"
    assert rel.type == rel_type, f"Expected type {rel_type!r}, got {rel.type!r}"
    assert rel.source_id == src
    assert rel.target_id == tgt


@then(parsers.parse('"{rel_id}" appears in relations for object "{obj_id}"'))
def check_rel_in_object_relations(world_ctx, rel_id, obj_id):
    rels = world_ctx["world"].get_relations(obj_id)
    ids = [r.id for r in rels]
    assert rel_id in ids, f"Relation {rel_id!r} not in relations for {obj_id!r}; got {ids}"


@then('the world context shows budget exhausted')
def check_budget_exhausted_flag(world_ctx):
    assert world_ctx["world"].context.get("budget_exhausted") is True


@then(parsers.parse('the world contains a "{rel_type}" relation from "{src}" to "{tgt}"'))
def check_relation_by_type_and_endpoints(world_ctx, rel_type, src, tgt):
    matches = [
        r for r in world_ctx["world"].relations.values()
        if r.type == rel_type and r.source_id == src and r.target_id == tgt
    ]
    assert matches, f"No {rel_type!r} relation from {src!r} to {tgt!r} in world"


@then(parsers.parse('I get back an object of type "{obj_type}" with data {data_json}'))
def check_lookup_object(lookup_result, obj_type, data_json):
    assert lookup_result is not None, "Expected an object but got None"
    assert lookup_result.type == obj_type
    assert lookup_result.data == json.loads(data_json)


@then('the object lookup returns nothing')
def check_lookup_nothing(lookup_result):
    assert lookup_result is None


@then(parsers.parse('I get back {count:d} relations'))
def check_relation_count(lookup_rels, count):
    assert len(lookup_rels) == count, f"Expected {count} relations, got {len(lookup_rels)}"


@then(parsers.parse('I get back {count:d} relation of type "{rel_type}"'))
def check_typed_relation_count(lookup_rels, count, rel_type):
    assert len(lookup_rels) == count
    assert all(r.type == rel_type for r in lookup_rels)


@then(parsers.parse('the restored world contains object "{obj_id}" with data {data_json}'))
def check_restored_object_data(snap_result, obj_id, data_json):
    assert snap_result is not None, "Snapshot returned None"
    world, _ = snap_result
    assert obj_id in world.objects
    assert world.objects[obj_id].data == json.loads(data_json)


@then(parsers.parse('the restored world contains relation "{rel_id}" of type "{rel_type}"'))
def check_restored_relation(snap_result, rel_id, rel_type):
    assert snap_result is not None
    world, _ = snap_result
    assert rel_id in world.relations
    assert world.relations[rel_id].type == rel_type


@then(parsers.parse('the restored ledger position is {position:d}'))
def check_restored_position(snap_result, position):
    assert snap_result is not None
    _, pos = snap_result
    assert pos == position, f"Expected position {position}, got {pos}"


@then('the snapshot file exists under the custom path')
def check_file_in_custom_dir(world_ctx):
    snap_dir = world_ctx["snap_dir"]
    files = list(snap_dir.glob("*.json"))
    assert files, f"No snapshot files under {snap_dir}"


@then('the snapshot load returns nothing')
def check_snap_none(snap_result):
    assert snap_result is None


@then('the snapshot directory exists')
def check_snap_dir_created(world_ctx):
    assert world_ctx["snap_dir"].exists()


@then(parsers.parse('the restored world contains object "{obj_id}"'))
def check_restored_has_object(snap_result, obj_id):
    assert snap_result is not None
    world, _ = snap_result
    assert obj_id in world.objects, f"{obj_id!r} not in restored world"


@then(parsers.parse('the restored world does not contain object "{obj_id}"'))
def check_restored_lacks_object(snap_result, obj_id):
    assert snap_result is not None
    world, _ = snap_result
    assert obj_id not in world.objects, f"{obj_id!r} unexpectedly in restored world"


@then(parsers.parse('"{obj_id}" has type "{obj_type}"'))
def check_object_type(world_ctx, obj_id, obj_type):
    obj = world_ctx["world"].objects.get(obj_id)
    assert obj is not None, f"Object {obj_id!r} not in world"
    assert obj.type == obj_type, f"Expected type {obj_type!r}, got {obj.type!r}"


@then(parsers.parse('the world contains relation "{rel_id}"'))
def check_world_has_relation(world_ctx, rel_id):
    assert rel_id in world_ctx["world"].relations, f"Relation {rel_id!r} not in world"


@then(parsers.parse('relation "{rel_id}" has data {data_json}'))
def check_relation_data(world_ctx, rel_id, data_json):
    rel = world_ctx["world"].relations.get(rel_id)
    assert rel is not None, f"Relation {rel_id!r} not in world"
    assert rel.data == json.loads(data_json)


@then('both resulting worlds contain the same objects')
def check_both_worlds_same_objects(order_ctx):
    fwd = set(order_ctx["forward"].objects.keys())
    rev = set(order_ctx["reverse"].objects.keys())
    assert fwd == rev, f"Worlds differ: forward={fwd}, reverse={rev}"


@then('the restored world context does not show budget exhausted')
def check_restored_no_budget_flag(snap_result):
    assert snap_result is not None
    world, _ = snap_result
    assert not world.context.get("budget_exhausted"), "Context unexpectedly shows budget exhausted"


@then(parsers.parse('the snapshot for "{run_id}" exists'))
def check_snapshot_run_exists(world_ctx, run_id):
    path = world_ctx["snap_dir"] / f"{run_id}.json"
    assert path.exists(), f"Snapshot {path} does not exist"


@then(parsers.parse('the snapshot file for "{run_id}" is valid JSON'))
def check_snapshot_valid_json(world_ctx, run_id):
    path = world_ctx["snap_dir"] / f"{run_id}.json"
    payload = json.loads(path.read_text())
    world_ctx["_snap_payload"] = payload


@then('it has a "world" key containing "objects" and "relations" lists')
def check_json_world_structure(world_ctx):
    p = world_ctx["_snap_payload"]
    assert "world" in p
    assert isinstance(p["world"]["objects"], list)
    assert isinstance(p["world"]["relations"], list)


@then(parsers.parse('it has a "position" integer equal to {position:d}'))
def check_json_position(world_ctx, position):
    assert world_ctx["_snap_payload"]["position"] == position


@then('the restored world contains no objects')
def check_restored_no_objects(snap_result):
    assert snap_result is not None
    world, _ = snap_result
    assert world.objects == {}


@then('the restored world contains no relations')
def check_restored_no_relations(snap_result):
    assert snap_result is not None
    world, _ = snap_result
    assert world.relations == {}
