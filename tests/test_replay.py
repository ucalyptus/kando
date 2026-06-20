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


def test_replay_strict_empty_ledger_returns_empty_world():
    """Strict replay on an empty ledger returns an empty world."""
    store = MemoryLedgerStore("strict-replay-empty")
    runtime = Runtime(ledger=store, responders=[])
    world = runtime.replay(strict=True)
    assert world.objects == {}


def test_replay_strict_produces_same_world_as_permissive():
    """Strict replay (re-fires responders) must match permissive (reproject) for deterministic kits."""
    from kando.schema.events import OBJECT_CREATED
    from datetime import datetime, timezone

    store = MemoryLedgerStore("strict-replay-parity")
    seed = KandoEvent("root-1", OBJECT_CREATED, "run:x", "cli", [], datetime.now(timezone.utc),
                      {"id": "obj-root", "type": "node", "data": {"v": 1}})
    store.append([seed])

    runtime = Runtime(ledger=store, responders=[])
    permissive_world = runtime.replay(strict=False)
    strict_world = runtime.replay(strict=True)

    assert set(permissive_world.objects.keys()) == set(strict_world.objects.keys())


def test_replay_empty_ledger():
    store = MemoryLedgerStore("empty-run")
    runtime = Runtime(ledger=store, responders=[])
    world = runtime.replay()
    assert world.objects == {}
    assert world.relations == {}


def test_strict_replay_raises_on_no_root_events():
    """replay(strict=True) must raise when all events have causes (no root events)."""
    import pytest
    from kando.ledger.memory import MemoryLedgerStore
    from kando.runtime import Runtime
    from kando.schema.events import make_event, OBJECT_CREATED

    ledger = MemoryLedgerStore("run:test-corrupt")

    # Create events where every event has a cause (no root events)
    e1 = make_event(type=OBJECT_CREATED, source="run:test", actor="test",
                    cause=["fake-root-id"], data={"id": "obj-1", "type": "thing"})
    e2 = make_event(type=OBJECT_CREATED, source="run:test", actor="test",
                    cause=[e1.id], data={"id": "obj-2", "type": "thing"})
    ledger.append([e1, e2])

    runtime = Runtime(ledger=ledger, responders=[])
    with pytest.raises(ValueError, match="no root"):
        runtime.replay(strict=True)
