"""Tests for the DeliveryBus and create_delivery_responder."""
from __future__ import annotations

from datetime import datetime, timezone

from kando.ledger.memory import MemoryLedgerStore
from kando.responders.delivery import DeliveryBus, create_delivery_responder
from kando.runtime import Runtime
from kando.schema.events import KandoEvent, OBJECT_CREATED
from kando.world.graph import World


def _ts():
    return datetime.now(timezone.utc)


def _evt(eid: str, etype: str = OBJECT_CREATED) -> KandoEvent:
    return KandoEvent(eid, etype, "run:t", "test", [], _ts(),
                      {"id": eid, "type": "x", "data": {}})


# ---------------------------------------------------------------------------
# DeliveryBus unit tests
# ---------------------------------------------------------------------------

def test_subscribe_and_deliver():
    received = []
    bus = DeliveryBus()
    bus.subscribe(received.append, name="collector")
    bus.deliver(_evt("e1"))
    assert len(received) == 1
    assert received[0].id == "e1"


def test_pattern_filter_receives_matching():
    hits = []
    bus = DeliveryBus()
    bus.subscribe(hits.append, name="filtered", pattern={"special.event"})
    bus.deliver(_evt("e1", "other.event"))
    bus.deliver(_evt("e2", "special.event"))
    assert len(hits) == 1
    assert hits[0].id == "e2"


def test_empty_pattern_matches_all():
    hits = []
    bus = DeliveryBus()
    bus.subscribe(hits.append, name="all")
    bus.deliver(_evt("a", "type.a"))
    bus.deliver(_evt("b", "type.b"))
    bus.deliver(_evt("c", "type.c"))
    assert len(hits) == 3


def test_deliver_returns_reached_subscriber_names():
    bus = DeliveryBus()
    bus.subscribe(lambda e: None, name="sub-a")
    bus.subscribe(lambda e: None, name="sub-b", pattern={"other.type"})
    reached = bus.deliver(_evt("e1", OBJECT_CREATED))
    assert "sub-a" in reached
    assert "sub-b" not in reached


def test_unsubscribe_removes_subscriber():
    hits = []
    bus = DeliveryBus()
    bus.subscribe(hits.append, name="temp")
    bus.deliver(_evt("before"))
    bus.unsubscribe("temp")
    bus.deliver(_evt("after"))
    assert len(hits) == 1


def test_unsubscribe_returns_false_for_unknown():
    bus = DeliveryBus()
    assert bus.unsubscribe("nonexistent") is False


def test_len_reflects_subscriber_count():
    bus = DeliveryBus()
    assert len(bus) == 0
    bus.subscribe(lambda e: None, name="s1")
    bus.subscribe(lambda e: None, name="s2")
    assert len(bus) == 2
    bus.unsubscribe("s1")
    assert len(bus) == 1


# ---------------------------------------------------------------------------
# Integration: create_delivery_responder plugs into Runtime
# ---------------------------------------------------------------------------

def test_delivery_responder_fires_for_every_event():
    received = []
    bus = DeliveryBus()
    bus.subscribe(received.append, name="log")
    delivery = create_delivery_responder(bus)

    store = MemoryLedgerStore("delivery-integration")
    seed = KandoEvent("seed-1", OBJECT_CREATED, "run:t", "cli", [], _ts(),
                      {"id": "obj-1", "type": "node", "data": {}})
    Runtime(ledger=store, responders=[delivery]).run([seed])

    # Seed event should have been delivered
    assert any(e.id == "seed-1" for e in received)


def test_delivery_responder_emits_no_new_events():
    received = []
    bus = DeliveryBus()
    bus.subscribe(received.append, name="log")
    delivery = create_delivery_responder(bus)

    store = MemoryLedgerStore("delivery-no-emit")
    seed = KandoEvent("seed-2", OBJECT_CREATED, "run:t", "cli", [], _ts(),
                      {"id": "obj-2", "type": "node", "data": {}})
    Runtime(ledger=store, responders=[delivery]).run([seed])

    # Only the seed event should be in the ledger (delivery responder emits nothing)
    all_events = list(store.read_all())
    non_seed = [e for e in all_events if e.id != "seed-2"]
    assert len(non_seed) == 0
