"""Tests for responder crash behaviour and DeliveryBus subscriber isolation."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator

import pytest

from kando.ledger.memory import MemoryLedgerStore
from kando.responders.base import Responder
from kando.responders.delivery import DeliveryBus, create_delivery_responder
from kando.runtime import Runtime
from kando.schema.events import KandoEvent, OBJECT_CREATED
from kando.world.graph import World


def _ts():
    return datetime.now(timezone.utc)


def _evt(eid: str) -> KandoEvent:
    return KandoEvent(eid, OBJECT_CREATED, "run:t", "test", [], _ts(),
                      {"id": eid, "type": "x", "data": {}})


def test_crashing_responder_propagates_out_of_runtime():
    """A responder that raises must propagate the exception out of runtime.run()."""
    def bad_responder(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
        raise ValueError("simulated crash")
        yield  # make it a generator

    r = Responder(name="bad", pattern=frozenset({OBJECT_CREATED}), fn=bad_responder)
    store = MemoryLedgerStore("crash-test")
    runtime = Runtime(ledger=store, responders=[r])

    with pytest.raises(ValueError, match="simulated crash"):
        runtime.run([_evt("s1")])


def test_delivery_bus_subscriber_exception_does_not_crash_deliver():
    """A failing subscriber must not prevent other subscribers from receiving the event."""
    bus = DeliveryBus()
    received: list[str] = []

    bus.subscribe(lambda e: (_ for _ in ()).throw(RuntimeError("bad subscriber")),
                  name="bad-sub", pattern=None)
    bus.subscribe(lambda e: received.append(e.id), name="good-sub", pattern=None)

    event = _evt("ev1")
    reached = bus.deliver(event)

    # good-sub should have received the event despite bad-sub failing
    assert "good-sub" in reached
    assert "bad-sub" not in reached
    assert "ev1" in received


def test_delivery_bus_subscriber_exception_does_not_crash_runtime():
    """When a DeliveryBus subscriber raises, the runtime loop must continue."""
    bus = DeliveryBus()
    bus.subscribe(lambda e: (_ for _ in ()).throw(RuntimeError("subscriber crash")),
                  name="crasher", pattern=None)

    store = MemoryLedgerStore("bus-crash-test")
    runtime = Runtime(ledger=store, responders=[create_delivery_responder(bus)])

    # Should not raise even though the subscriber crashes
    world = runtime.run([_evt("s1")])
    assert "s1" in world.objects
