"""Targeted tests to kill surviving and 'no tests' mutants from mutmut."""
from __future__ import annotations
from datetime import datetime, timezone
from kando.schema.events import KandoEvent, OBJECT_CREATED, OBJECT_PATCHED, RELATION_CREATED, RELATION_REMOVED
from kando.world.graph import World, WorldObject, Relation
from kando.world.projection import apply, project
from kando.ledger.memory import MemoryLedgerStore
from kando.ledger.interface import LedgerStore
from kando.trace.lineage import build_lineage_index, trace, explain
from kando.branch.replay import read_branch
from kando.branch.fork import fork


def _ts():
    return datetime.now(timezone.utc)


def _make_event(eid: str, etype: str, data: dict, cause=None) -> KandoEvent:
    return KandoEvent(
        id=eid,
        type=etype,
        source="run:mut-test",
        actor="test",
        cause=cause or [],
        timestamp=_ts(),
        data=data,
    )


# ---------------------------------------------------------------------------
# Kill: kando.world.projection.x_apply__mutmut_5  (id=None)
# Kill: kando.world.projection.x_apply__mutmut_6  (type=None)
# ---------------------------------------------------------------------------
def test_apply_object_created_sets_correct_id():
    world = World()
    event = _make_event("e1", OBJECT_CREATED, {"id": "my-obj", "type": "claim", "data": {}})
    apply(world, event)
    assert world.objects["my-obj"].id == "my-obj"


def test_apply_object_created_sets_correct_type():
    world = World()
    event = _make_event("e1", OBJECT_CREATED, {"id": "o1", "type": "goal", "data": {}})
    apply(world, event)
    assert world.objects["o1"].type == "goal"


# ---------------------------------------------------------------------------
# Kill: kando.world.projection.x_apply__mutmut_17 (data default None)
# Kill: kando.world.projection.x_apply__mutmut_19 (data default empty)
# ---------------------------------------------------------------------------
def test_apply_object_created_with_no_data_key_defaults_to_empty():
    world = World()
    event = _make_event("e1", OBJECT_CREATED, {"id": "o1", "type": "claim"})  # no "data" key
    apply(world, event)
    assert world.objects["o1"].data == {}


def test_apply_object_created_data_is_dict():
    world = World()
    event = _make_event("e1", OBJECT_CREATED, {"id": "o1", "type": "claim", "data": {"k": "v"}})
    apply(world, event)
    assert isinstance(world.objects["o1"].data, dict)
    assert world.objects["o1"].data == {"k": "v"}


# ---------------------------------------------------------------------------
# Kill: kando.world.projection.x_apply__mutmut_29 (patch default None)
# Kill: kando.world.projection.x_apply__mutmut_31 (patch default empty)
# ---------------------------------------------------------------------------
def test_apply_object_patched_with_no_patch_key_is_noop():
    world = World()
    apply(world, _make_event("e1", OBJECT_CREATED, {"id": "o1", "type": "claim", "data": {"x": 1}}))
    # Event with no "patch" key — should not crash, should leave data unchanged
    event = _make_event("e2", OBJECT_PATCHED, {"id": "o1"})
    apply(world, event)
    assert world.objects["o1"].data == {"x": 1}


# ---------------------------------------------------------------------------
# Kill: kando.world.projection.x_apply__mutmut_38 (relation id=None)
# Kill: kando.world.projection.x_apply__mutmut_40 (source_id=None)
# Kill: kando.world.projection.x_apply__mutmut_41 (target_id=None)
# Kill: kando.world.projection.x_apply__mutmut_42 (data=None)
# Kill: kando.world.projection.x_apply__mutmut_47 (data missing)
# Kill: kando.world.projection.x_apply__mutmut_57 (data key=None)
# Kill: kando.world.projection.x_apply__mutmut_61 (data key="XXdataXX")
# Kill: kando.world.projection.x_apply__mutmut_62 (data key="DATA")
# ---------------------------------------------------------------------------
def test_apply_relation_created_sets_correct_fields():
    world = World()
    event = _make_event("e1", RELATION_CREATED, {
        "id": "rel-1",
        "type": "supports",
        "source_id": "src",
        "target_id": "tgt",
        "data": {"weight": 1},
    })
    apply(world, event)
    rel = world.relations["rel-1"]
    assert rel.id == "rel-1"
    assert rel.type == "supports"
    assert rel.source_id == "src"
    assert rel.target_id == "tgt"
    assert rel.data == {"weight": 1}


def test_apply_relation_created_data_defaults_to_empty():
    world = World()
    event = _make_event("e1", RELATION_CREATED, {
        "id": "rel-2",
        "type": "blocks",
        "source_id": "a",
        "target_id": "b",
        # no "data" key
    })
    apply(world, event)
    assert world.relations["rel-2"].data == {}


# ---------------------------------------------------------------------------
# Kill: mutmut_63 (RELATION_REMOVED condition flipped)
# Kill: mutmut_64 (pop key=None)
# Kill: mutmut_65 (pop without default)
# Kill: mutmut_66 (pop with empty)
# Kill: mutmut_67 (pop key "XXidXX")
# Kill: mutmut_68 (pop key "ID")
# ---------------------------------------------------------------------------
def test_apply_relation_removed_removes_correct_relation():
    world = World()
    apply(world, _make_event("e1", RELATION_CREATED, {
        "id": "rel-1", "type": "supports", "source_id": "a", "target_id": "b"
    }))
    apply(world, _make_event("e2", RELATION_CREATED, {
        "id": "rel-2", "type": "blocks", "source_id": "c", "target_id": "d"
    }))
    apply(world, _make_event("e3", RELATION_REMOVED, {"id": "rel-1"}))
    assert "rel-1" not in world.relations
    assert "rel-2" in world.relations


def test_apply_relation_removed_nonexistent_is_noop():
    world = World()
    event = _make_event("e1", RELATION_REMOVED, {"id": "ghost-rel"})
    apply(world, event)  # should not raise
    assert len(world.relations) == 0


def test_apply_relation_removed_does_not_remove_other_relations():
    world = World()
    apply(world, _make_event("e1", RELATION_CREATED, {
        "id": "rel-keep", "type": "supports", "source_id": "a", "target_id": "b"
    }))
    apply(world, _make_event("e2", RELATION_REMOVED, {"id": "rel-delete"}))
    assert "rel-keep" in world.relations


# ---------------------------------------------------------------------------
# Kill: kando.ledger.memory.xǁMemoryLedgerStoreǁread__mutmut_1 (default=1)
# ---------------------------------------------------------------------------
def test_memory_ledger_read_default_from_position_is_zero():
    store = MemoryLedgerStore("test")
    events = [
        _make_event(f"e{i}", OBJECT_CREATED, {"id": f"o{i}", "type": "t", "data": {}})
        for i in range(5)
    ]
    store.append(events)
    # Default from_position=0 should return ALL events
    result = list(store.read())
    assert len(result) == 5
    assert result[0].id == "e0"


# ---------------------------------------------------------------------------
# Kill: kando.ledger.interface.xǁLedgerStoreǁread_all__mutmut_1 (from_position=None)
# ---------------------------------------------------------------------------
def test_ledger_read_all_starts_from_position_zero():
    store = MemoryLedgerStore("test")
    events = [
        _make_event(f"e{i}", OBJECT_CREATED, {"id": f"o{i}", "type": "t", "data": {}})
        for i in range(3)
    ]
    store.append(events)
    result = list(store.read_all())
    assert len(result) == 3
    assert result[0].id == "e0"


def test_ledger_read_rejects_none_position():
    """Kills mutmut: read_all passing from_position=None instead of 0."""
    import pytest
    store = MemoryLedgerStore("test")
    with pytest.raises(TypeError, match="from_position must be an int, got None"):
        list(store.read(from_position=None))


# ---------------------------------------------------------------------------
# Kill: kando.trace.lineage.x_trace__mutmut_8 (continue → break)
# ---------------------------------------------------------------------------
def test_trace_with_diamond_does_not_stop_at_first_seen():
    # Diamond: e0 ← e1 and e0 ← e2, with e3 depending on both e1 and e2
    # e3 -> [e1, e2], e1 -> [e0], e2 -> [e0]
    events = [
        _make_event("e0", OBJECT_CREATED, {}, cause=[]),
        _make_event("e1", OBJECT_CREATED, {}, cause=["e0"]),
        _make_event("e2", OBJECT_CREATED, {}, cause=["e0"]),
        _make_event("e3", OBJECT_CREATED, {}, cause=["e1", "e2"]),
    ]
    index = build_lineage_index(events)
    chain = trace("e3", index)
    # With 'break' instead of 'continue', the traversal stops at first duplicate
    # So we need to verify e0 only appears once but all nodes are visited
    assert "e0" in chain
    assert "e1" in chain
    assert "e2" in chain
    assert "e3" in chain
    assert chain.count("e0") == 1  # should appear only once despite diamond


# ---------------------------------------------------------------------------
# Kill: kando.trace.lineage.x_trace__mutmut_9 (seen.add(None))
# ---------------------------------------------------------------------------
def test_trace_does_not_revisit_seen_events():
    # Linear chain with a cycle potential: e0 -> e1 -> e2 -> e0 (circular)
    # But lineage is typically acyclic; this tests that seen prevents infinite loop
    events = [
        _make_event("e0", OBJECT_CREATED, {}, cause=[]),
        _make_event("e1", OBJECT_CREATED, {}, cause=["e0"]),
        _make_event("e2", OBJECT_CREATED, {}, cause=["e1"]),
    ]
    index = build_lineage_index(events)
    # Add a fake back-reference to test loop protection
    index["e2"] = ["e1", "e0"]
    chain = trace("e2", index)
    # e0 should appear exactly once (not revisited)
    assert chain.count("e0") == 1


def test_trace_continue_not_break_on_duplicate():
    """When a duplicate is seen, we should CONTINUE (skip) not BREAK (stop).
    Kills mutmut_8: change of 'continue' to 'break'.

    Diamond with two roots:
      e_r1 <- e1 <- e3
      e_r1 <- e2 (e2 also caused by e_r1)
      e_r2 <- e2
      e3 caused by [e1, e2]
    When tracing e3, queue after processing e2 will have [e_r1, e_r1, e_r2].
    With 'continue' we skip the second e_r1 but still visit e_r2.
    With 'break' we stop when we see the duplicate e_r1, missing e_r2.
    """
    index = {
        "e3": ["e1", "e2"],
        "e1": ["e_r1"],
        "e2": ["e_r1", "e_r2"],
        "e_r1": [],
        "e_r2": [],
    }
    chain = trace("e3", index)
    assert "e_r2" in chain, (
        "e_r2 must be in chain — 'break' on duplicate would stop before reaching it"
    )
    assert "e_r1" in chain
    assert chain.count("e_r1") == 1


# ---------------------------------------------------------------------------
# Kill: world.graph.get_object__mutmut_1 (return None instead of objects.get)
# ---------------------------------------------------------------------------
def test_world_get_object_returns_correct_object():
    world = World()
    world.objects["o1"] = WorldObject(id="o1", type="claim", data={"x": 1})
    result = world.get_object("o1")
    assert result is not None
    assert result.id == "o1"


def test_world_get_object_returns_none_for_missing():
    world = World()
    result = world.get_object("nonexistent")
    assert result is None


# ---------------------------------------------------------------------------
# Kill: world.graph.get_relations__mutmut_1 (rels = None)
# Kill: world.graph._relations_for_object__mutmut_1 (or → and)
# ---------------------------------------------------------------------------
def test_get_relations_source_only():
    world = World()
    world.relations["r1"] = Relation(id="r1", type="supports", source_id="a", target_id="b")
    world.relations["r2"] = Relation(id="r2", type="blocks", source_id="c", target_id="d")
    rels = world.get_relations("a")
    assert len(rels) == 1
    assert rels[0].id == "r1"


def test_get_relations_target_only():
    world = World()
    world.relations["r1"] = Relation(id="r1", type="supports", source_id="a", target_id="b")
    rels = world.get_relations("b")
    assert len(rels) == 1
    assert rels[0].id == "r1"


def test_get_relations_filtered_by_type():
    world = World()
    world.relations["r1"] = Relation(id="r1", type="supports", source_id="a", target_id="b")
    world.relations["r2"] = Relation(id="r2", type="blocks", source_id="a", target_id="c")
    supports = world.get_relations("a", relation_type="supports")
    assert len(supports) == 1
    assert supports[0].id == "r1"


def test_get_relations_empty_world():
    world = World()
    rels = world.get_relations("a")
    assert rels == []


# ---------------------------------------------------------------------------
# Kill: branch.replay.x_read_branch__mutmut_1 (from_position=None)
# Kill: branch.replay.x_read_branch__mutmut_2 (from_position=1)
# Kill: branch.replay.x_read_branch__mutmut_3 (second from_position=None)
# Kill: branch.replay.x_read_branch__mutmut_4 (second from_position=1)
# ---------------------------------------------------------------------------
def test_read_branch_yields_all_parent_events_from_position_zero():
    parent_store = MemoryLedgerStore("parent")
    branch_store = MemoryLedgerStore("branch")

    parent_events = [
        _make_event(f"p{i}", OBJECT_CREATED, {"id": f"po{i}", "type": "t", "data": {}})
        for i in range(3)
    ]
    branch_events = [
        _make_event(f"b{i}", OBJECT_CREATED, {"id": f"bo{i}", "type": "t", "data": {}})
        for i in range(2)
    ]
    parent_store.append(parent_events)
    branch_store.append(branch_events)

    meta = fork("parent", 3, "branch")
    all_events = list(read_branch(meta, parent_store, branch_store))

    # Should include ALL parent events (from position 0) plus ALL branch events
    assert len(all_events) == 5
    parent_ids = {e.id for e in all_events if e.id.startswith("p")}
    branch_ids = {e.id for e in all_events if e.id.startswith("b")}
    assert parent_ids == {"p0", "p1", "p2"}
    assert branch_ids == {"b0", "b1"}


def test_read_branch_empty_parent_yields_only_branch():
    parent_store = MemoryLedgerStore("parent")
    branch_store = MemoryLedgerStore("branch")

    branch_events = [
        _make_event("b0", OBJECT_CREATED, {"id": "bo0", "type": "t", "data": {}})
    ]
    branch_store.append(branch_events)

    meta = fork("parent", 0, "branch")
    all_events = list(read_branch(meta, parent_store, branch_store))
    assert len(all_events) == 1
    assert all_events[0].id == "b0"


def test_read_branch_includes_first_parent_event():
    """Specifically ensures from_position=0, not 1 (kills mutmut_2)."""
    parent_store = MemoryLedgerStore("parent")
    branch_store = MemoryLedgerStore("branch")

    parent_store.append([
        _make_event("p0", OBJECT_CREATED, {"id": "po0", "type": "t", "data": {}}),
        _make_event("p1", OBJECT_CREATED, {"id": "po1", "type": "t", "data": {}}),
    ])

    meta = fork("parent", 2, "branch")
    all_events = list(read_branch(meta, parent_store, branch_store))
    ids = [e.id for e in all_events]
    assert "p0" in ids, "First parent event (p0) must be included — from_position must be 0, not 1"
