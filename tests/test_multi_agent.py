"""Tests for multi-agent / multi-runtime isolation."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator

import pytest

from kando.ledger.memory import MemoryLedgerStore
from kando.responders.base import Responder
from kando.runtime import Runtime
from kando.schema.events import KandoEvent, OBJECT_CREATED
from kando.world.graph import World


def _ts():
    return datetime.now(timezone.utc)


def _evt(eid: str, obj_id: str) -> KandoEvent:
    return KandoEvent(eid, OBJECT_CREATED, "run:test", "test", [], _ts(),
                      {"id": obj_id, "type": "node", "data": {}})


def test_two_runtimes_do_not_share_state():
    """Two Runtime instances with separate MemoryLedgerStores must not interfere."""
    store_a = MemoryLedgerStore("run-a")
    store_b = MemoryLedgerStore("run-b")

    runtime_a = Runtime(ledger=store_a, responders=[])
    runtime_b = Runtime(ledger=store_b, responders=[])

    world_a = runtime_a.run([_evt("a1", "obj-alpha")])
    world_b = runtime_b.run([_evt("b1", "obj-beta")])

    # Each world contains only its own object
    assert "obj-alpha" in world_a.objects
    assert "obj-beta" not in world_a.objects

    assert "obj-beta" in world_b.objects
    assert "obj-alpha" not in world_b.objects

    # Ledgers are independent
    events_a = list(store_a.read_all())
    events_b = list(store_b.read_all())
    assert all(e.id == "a1" for e in events_a)
    assert all(e.id == "b1" for e in events_b)


def test_two_runtimes_with_same_responder_class_do_not_interfere():
    """Responder state (if any) must not bleed between independently constructed runtimes."""
    calls_a: list[str] = []
    calls_b: list[str] = []

    def responder_a(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
        calls_a.append(event.id)
        return iter([])

    def responder_b(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
        calls_b.append(event.id)
        return iter([])

    r_a = Responder(name="r", pattern=frozenset({OBJECT_CREATED}), fn=responder_a)
    r_b = Responder(name="r", pattern=frozenset({OBJECT_CREATED}), fn=responder_b)

    Runtime(ledger=MemoryLedgerStore("x"), responders=[r_a]).run([_evt("e-a", "oa")])
    Runtime(ledger=MemoryLedgerStore("y"), responders=[r_b]).run([_evt("e-b", "ob")])

    assert calls_a == ["e-a"]
    assert calls_b == ["e-b"]
