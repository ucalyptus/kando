"""Determinism contract: same ledger always projects to same world."""
import pytest
from datetime import datetime, timezone
from kando.ledger.memory import MemoryLedgerStore
from kando.world.projection import project
from kando.schema.events import KandoEvent, OBJECT_CREATED, OBJECT_PATCHED


def ts():
    return datetime.now(timezone.utc)


def test_projection_is_deterministic():
    events = [
        KandoEvent("e1", OBJECT_CREATED, "run:r", "t", [], ts(),
                   {"id": "o1", "type": "x", "data": {"v": 1}}),
        KandoEvent("e2", OBJECT_PATCHED, "run:r", "t", ["e1"], ts(),
                   {"id": "o1", "patch": {"v": 2}}),
    ]
    world_a = project(iter(events))
    world_b = project(iter(events))
    assert world_a.objects["o1"].data == world_b.objects["o1"].data == {"v": 2}


def test_projecting_in_reverse_order_fails():
    """Applying events in reverse order must NOT produce the same world as forward order."""
    events = [
        KandoEvent("e1", OBJECT_CREATED, "run:r", "t", [], ts(),
                   {"id": "o1", "type": "x", "data": {"v": 1}}),
        KandoEvent("e2", OBJECT_PATCHED, "run:r", "t", ["e1"], ts(),
                   {"id": "o1", "patch": {"v": 99}}),
    ]
    forward_world = project(iter(events))
    # Reverse: patch arrives before create — patched object doesn't exist yet, so patch is a no-op.
    reversed_world = project(iter(reversed(events)))
    # Forward world has v=99; reversed world has v=1 (patch was ignored).
    assert forward_world.objects["o1"].data["v"] == 99
    assert reversed_world.objects["o1"].data["v"] == 1
    assert forward_world.objects["o1"].data != reversed_world.objects["o1"].data


def test_multiple_independent_projections_are_identical():
    events = [
        KandoEvent("e1", OBJECT_CREATED, "run:r", "t", [], ts(),
                   {"id": "o1", "type": "a", "data": {"x": 10}}),
        KandoEvent("e2", OBJECT_CREATED, "run:r", "t", ["e1"], ts(),
                   {"id": "o2", "type": "b", "data": {"y": 20}}),
    ]
    worlds = [project(iter(events)) for _ in range(5)]
    for w in worlds:
        assert w.objects["o1"].data == {"x": 10}
        assert w.objects["o2"].data == {"y": 20}
