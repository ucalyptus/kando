"""Fork, diff, and branch structure tests."""
import pytest
from kando.branch.fork import fork
from kando.branch.diff import diff
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
