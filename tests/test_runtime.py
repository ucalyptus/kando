"""Tests for the full runtime event loop."""
from __future__ import annotations
import pytest
from datetime import datetime, timezone
from typing import Iterator

from kando.ledger.memory import MemoryLedgerStore
from kando.responders.base import Responder
from kando.responders.budget import Budget
from kando.runtime import Runtime
from kando.schema.events import (
    KandoEvent, OBJECT_CREATED, OBJECT_PATCHED, BUDGET_EXHAUSTED, make_event
)
from kando.world.graph import World


def ts():
    return datetime.now(timezone.utc)


def evt(id: str, type: str, cause: list[str], data: dict) -> KandoEvent:
    return KandoEvent(id=id, type=type, source="run:test", actor="test",
                      cause=cause, timestamp=ts(), data=data)


# ---------------------------------------------------------------------------
# Test: seed events get appended to ledger
# ---------------------------------------------------------------------------

def test_seed_events_are_appended():
    store = MemoryLedgerStore("rt-1")
    runtime = Runtime(ledger=store, responders=[])

    seed = [
        evt("s1", OBJECT_CREATED, [], {"id": "obj-a", "type": "x", "data": {}}),
        evt("s2", OBJECT_CREATED, ["s1"], {"id": "obj-b", "type": "y", "data": {}}),
    ]
    runtime.run(seed)

    appended = list(store.read_all())
    ids = [e.id for e in appended]
    assert "s1" in ids
    assert "s2" in ids


# ---------------------------------------------------------------------------
# Test: responders fire and their output events are processed
# ---------------------------------------------------------------------------

def test_responder_fires_and_output_is_processed():
    store = MemoryLedgerStore("rt-2")

    def echo_responder(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
        yield evt("r-echo", OBJECT_CREATED, [event.id],
                  {"id": "echo-obj", "type": "echo", "data": {"from": event.id}})

    r = Responder(name="echo", pattern=frozenset({OBJECT_CREATED}), fn=echo_responder)
    runtime = Runtime(ledger=store, responders=[r])

    seed = [evt("s1", OBJECT_CREATED, [], {"id": "obj-1", "type": "thing", "data": {}})]
    world = runtime.run(seed)

    # echo-obj should have been created by the responder
    assert "echo-obj" in world.objects
    # and the echo event should be in the ledger
    all_ids = [e.id for e in store.read_all()]
    assert "r-echo" in all_ids


# ---------------------------------------------------------------------------
# Test: budget exhaustion stops the loop
# ---------------------------------------------------------------------------

def test_budget_exhaustion_stops_loop():
    store = MemoryLedgerStore("rt-3")

    def infinite_responder(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
        # Would loop forever — budget must stop it.
        yield evt(f"inf-{event.id}", OBJECT_CREATED, [event.id],
                  {"id": f"inf-{event.id}", "type": "inf", "data": {}})

    r = Responder(name="inf", pattern=frozenset({OBJECT_CREATED}), fn=infinite_responder)
    tight_budget = Budget(max_events=5)
    runtime = Runtime(ledger=store, responders=[r], budget=tight_budget)

    seed = [evt("s1", OBJECT_CREATED, [], {"id": "obj-seed", "type": "x", "data": {}})]
    world = runtime.run(seed)

    all_events = list(store.read_all())
    types = [e.type for e in all_events]
    assert BUDGET_EXHAUSTED in types


# ---------------------------------------------------------------------------
# Test: world reflects all committed events
# ---------------------------------------------------------------------------

def test_world_reflects_all_committed_events():
    store = MemoryLedgerStore("rt-4")
    runtime = Runtime(ledger=store, responders=[])

    seed = [
        evt("s1", OBJECT_CREATED, [], {"id": "obj-x", "type": "node", "data": {"v": 1}}),
        evt("s2", OBJECT_PATCHED, ["s1"], {"id": "obj-x", "patch": {"v": 2}}),
    ]
    world = runtime.run(seed)

    assert "obj-x" in world.objects
    assert world.objects["obj-x"].data["v"] == 2


# ---------------------------------------------------------------------------
# Test: responder exceptions propagate (fail loudly)
# ---------------------------------------------------------------------------

def test_responder_exception_propagates():
    store = MemoryLedgerStore("rt-5")

    def bad_responder(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
        raise RuntimeError("intentional failure")
        yield  # make it a generator

    r = Responder(name="bad", pattern=frozenset({OBJECT_CREATED}), fn=bad_responder)
    runtime = Runtime(ledger=store, responders=[r])

    seed = [evt("s1", OBJECT_CREATED, [], {"id": "boom", "type": "x", "data": {}})]
    with pytest.raises(RuntimeError, match="intentional failure"):
        runtime.run(seed)


# ---------------------------------------------------------------------------
# Test: make_event factory produces UUID-based IDs
# ---------------------------------------------------------------------------

def test_make_event_uuid_id():
    e = make_event(OBJECT_CREATED, "run:x", "actor", [], {"id": "o", "type": "t", "data": {}})
    assert e.id.startswith(f"{OBJECT_CREATED}-")
    assert len(e.id) == len(OBJECT_CREATED) + 1 + 8  # "type-" + 8 hex chars
    assert e.type == OBJECT_CREATED


def test_make_event_unique_ids():
    e1 = make_event(OBJECT_CREATED, "run:x", "actor", [], {"id": "o", "type": "t", "data": {}})
    e2 = make_event(OBJECT_CREATED, "run:x", "actor", [], {"id": "o", "type": "t", "data": {}})
    assert e1.id != e2.id


# ---------------------------------------------------------------------------
# Test: run on pre-populated ledger starts from correct world
# ---------------------------------------------------------------------------

def test_run_starts_from_existing_world():
    store = MemoryLedgerStore("rt-6")
    # Pre-populate the ledger
    store.append([
        evt("pre1", OBJECT_CREATED, [], {"id": "existing", "type": "node", "data": {"init": True}}),
    ])
    runtime = Runtime(ledger=store, responders=[])
    new_event = evt("new1", OBJECT_PATCHED, ["pre1"], {"id": "existing", "patch": {"updated": True}})
    world = runtime.run([new_event])

    assert "existing" in world.objects
    assert world.objects["existing"].data.get("init") is True
    assert world.objects["existing"].data.get("updated") is True


def test_runtime_exposes_cache_on_world_context():
    from kando.cache.llm import LLMCache
    cache = LLMCache()
    cache.put({"model": "x", "prompt": "hello"}, {"text": "world"})

    store = MemoryLedgerStore("cache-wiring-test")
    runtime = Runtime(ledger=store, responders=[], cache=cache)
    world = runtime.run([evt("seed", OBJECT_CREATED, [], {"id": "obj", "type": "T", "data": {}})])

    assert "cache" in world.context
    assert world.context["cache"] is cache
    assert len(world.context["cache"]) == 1


def test_runtime_creates_default_cache_when_none_provided():
    from kando.cache.llm import LLMCache
    store = MemoryLedgerStore("cache-default-test")
    runtime = Runtime(ledger=store, responders=[])
    world = runtime.run([evt("s", OBJECT_CREATED, [], {"id": "o", "type": "T", "data": {}})])
    assert "cache" in world.context
    assert isinstance(world.context["cache"], LLMCache)
