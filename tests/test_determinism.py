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
