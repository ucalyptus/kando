"""Strict and permissive replay produce consistent world state."""
import pytest
from datetime import datetime, timezone
from kando.ledger.memory import MemoryLedgerStore
from kando.runtime import Runtime
from kando.world.projection import project, reproject
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


def test_replay_same_as_direct_projection():
    """replay() must produce the same world as projecting the store directly."""
    store = MemoryLedgerStore("replay-parity")
    events = [
        KandoEvent("r1", OBJECT_CREATED, "run:r", "test", [], ts(),
                   {"id": "x", "type": "node", "data": {"v": 42}}),
        KandoEvent("r2", OBJECT_CREATED, "run:r", "test", ["r1"], ts(),
                   {"id": "y", "type": "node", "data": {"v": 7}}),
        KandoEvent("r3", RELATION_CREATED, "run:r", "test", ["r1", "r2"], ts(),
                   {"id": "e1", "type": "depends_on", "source_id": "x", "target_id": "y"}),
    ]
    store.append(events)

    runtime = Runtime(ledger=store, responders=[])
    replayed = runtime.replay(strict=False)
    direct = reproject(store)

    assert set(replayed.objects.keys()) == set(direct.objects.keys())
    assert set(replayed.relations.keys()) == set(direct.relations.keys())
    for oid in direct.objects:
        assert replayed.objects[oid].data == direct.objects[oid].data


def test_replay_strict_raises():
    store = MemoryLedgerStore("strict-replay")
    runtime = Runtime(ledger=store, responders=[])
    with pytest.raises(NotImplementedError):
        runtime.replay(strict=True)


def test_replay_empty_ledger():
    store = MemoryLedgerStore("empty-run")
    runtime = Runtime(ledger=store, responders=[])
    world = runtime.replay()
    assert world.objects == {}
    assert world.relations == {}
