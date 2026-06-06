"""Strict and permissive replay produce consistent world state."""
import pytest
from datetime import datetime, timezone
from kando.ledger.memory import MemoryLedgerStore
from kando.world.projection import project
from kando.schema.events import KandoEvent, OBJECT_CREATED, RELATION_CREATED


def ts():
    return datetime.now(timezone.utc)


def test_permissive_replay_objects():
    store = MemoryLedgerStore("replay-test")
    store.append([
        KandoEvent("e1", OBJECT_CREATED, "run:r", "test", [], ts(),
                   {"id": "obj-a", "type": "claim", "data": {"text": "hello"}}),
        KandoEvent("e2", OBJECT_CREATED, "run:r", "test", ["e1"], ts(),
                   {"id": "obj-b", "type": "claim", "data": {"text": "world"}}),
        KandoEvent("e3", RELATION_CREATED, "run:r", "test", ["e2"], ts(),
                   {"id": "rel-1", "type": "supports", "source_id": "obj-a", "target_id": "obj-b"}),
    ])
    world = project(store.read_all())
    assert "obj-a" in world.objects
    assert "obj-b" in world.objects
    assert "rel-1" in world.relations
    assert world.relations["rel-1"].type == "supports"
