"""Fork, diff, and branch structure tests."""
import pytest
from kando.branch.fork import fork
from kando.branch.diff import diff, WorldDiff
from kando.world.graph import World, WorldObject, Relation


def test_fork_metadata():
    meta = fork("run-001", fork_position=250, branch_id="branch-001")
    assert meta.parent_run_id == "run-001"
    assert meta.fork_position == 250
    assert meta.branch_id == "branch-001"


def test_diff_added_object():
    a = World()
    b = World()
    b.objects["new-obj"] = WorldObject(id="new-obj", type="claim", data={})
    result = diff(a, b)
    assert "new-obj" in result.added_objects
    assert result.removed_objects == []


def test_diff_removed_relation():
    a = World()
    b = World()
    a.relations["rel-1"] = Relation("rel-1", "supports", "x", "y")
    result = diff(a, b)
    assert "rel-1" in result.removed_relations


def test_diff_patched_object():
    a = World()
    b = World()
    a.objects["obj-1"] = WorldObject(id="obj-1", type="claim", data={"v": 1})
    b.objects["obj-1"] = WorldObject(id="obj-1", type="claim", data={"v": 2})
    result = diff(a, b)
    assert "obj-1" in result.patched_objects
    assert result.added_objects == []
    assert result.removed_objects == []


def test_diff_bool_true_when_differences():
    a = World()
    b = World()
    b.objects["x"] = WorldObject(id="x", type="thing", data={})
    result = diff(a, b)
    assert bool(result) is True


def test_diff_bool_false_when_identical():
    a = World()
    b = World()
    for w in (a, b):
        w.objects["x"] = WorldObject(id="x", type="thing", data={"k": "v"})
    result = diff(a, b)
    assert bool(result) is False


def test_diff_summary_non_empty():
    a = World()
    b = World()
    b.objects["obj-new"] = WorldObject(id="obj-new", type="item", data={})
    result = diff(a, b)
    s = result.summary()
    assert "object" in s
    assert "+" in s


def test_diff_summary_no_changes():
    a = World()
    b = World()
    result = diff(a, b)
    assert result.summary() == "no changes"
