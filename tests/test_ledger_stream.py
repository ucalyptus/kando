"""Integration tests for EventStreamLedgerStore — requires a running EventStoreDB."""
from __future__ import annotations

import os
import time
import uuid

import pytest

from kando.ledger.stream import EventStreamLedgerStore, _make_uri
from kando.schema.events import KandoEvent, OBJECT_CREATED, make_event
from datetime import datetime, timezone

ESDB_AVAILABLE = True
try:
    from esdbclient import EventStoreDBClient
    from esdbclient.exceptions import NotFound
    _c = EventStoreDBClient(uri=_make_uri())
    list(_c.read_stream("$streams", limit=1))
except Exception:
    ESDB_AVAILABLE = False

requires_esdb = pytest.mark.skipif(
    not ESDB_AVAILABLE,
    reason="EventStoreDB not reachable — start with `docker compose up -d eventstore`",
)


def _unique_run() -> str:
    return f"test-{uuid.uuid4().hex[:8]}"


def _evt(eid: str, cause: list[str] | None = None) -> KandoEvent:
    return KandoEvent(
        id=eid, type=OBJECT_CREATED, source="run:test", actor="test",
        cause=cause or [], timestamp=datetime.now(timezone.utc),
        data={"id": eid, "type": "item", "data": {}},
    )


@requires_esdb
def test_append_and_read_all():
    store = EventStreamLedgerStore(_unique_run())
    e0, e1 = _evt("ev-0"), _evt("ev-1", ["ev-0"])
    pos = store.append([e0, e1])
    assert pos == 2
    events = list(store.read_all())
    assert len(events) == 2
    assert events[0].id == "ev-0"
    assert events[1].id == "ev-1"
    assert events[1].cause == ["ev-0"]


@requires_esdb
def test_read_from_position():
    store = EventStreamLedgerStore(_unique_run())
    store.append([_evt("a"), _evt("b"), _evt("c")])
    tail = list(store.read(from_position=2))
    assert len(tail) == 1
    assert tail[0].id == "c"


@requires_esdb
def test_empty_stream_returns_nothing():
    store = EventStreamLedgerStore(_unique_run())
    assert list(store.read_all()) == []


@requires_esdb
def test_append_empty_list_is_noop():
    store = EventStreamLedgerStore(_unique_run())
    pos = store.append([])
    assert pos == 0
    store.append([_evt("x")])
    pos2 = store.append([])
    assert pos2 == 1


@requires_esdb
def test_persistence_across_instances():
    run_id = _unique_run()
    store1 = EventStreamLedgerStore(run_id)
    store1.append([_evt("p0"), _evt("p1")])

    store2 = EventStreamLedgerStore(run_id)
    events = list(store2.read_all())
    assert len(events) == 2
    assert events[0].id == "p0"
    assert events[1].id == "p1"


@requires_esdb
def test_stream_name_format():
    store = EventStreamLedgerStore("my-run-42")
    assert store.stream_name() == "run:my-run-42"


@requires_esdb
def test_serialization_roundtrip_preserves_all_fields():
    store = EventStreamLedgerStore(_unique_run())
    now = datetime.now(timezone.utc)
    original = KandoEvent(
        id="roundtrip-1", type=OBJECT_CREATED, source="run:x",
        actor="unit-test", cause=["root-0"],
        timestamp=now,
        data={"nested": {"key": 42}, "list": [1, 2, 3]},
    )
    store.append([original])
    restored = list(store.read_all())[0]
    assert restored.id == original.id
    assert restored.type == original.type
    assert restored.source == original.source
    assert restored.actor == original.actor
    assert restored.cause == original.cause
    assert restored.data == original.data
    assert restored.timestamp.replace(microsecond=0) == now.replace(microsecond=0)


@requires_esdb
def test_make_uri_converts_http():
    assert _make_uri("http://localhost:2113") == "esdb://localhost:2113?tls=false"
    assert _make_uri("https://cloud.esdb.io:2113") == "esdb://cloud.esdb.io:2113"
    assert _make_uri("esdb://already:2113?tls=false") == "esdb://already:2113?tls=false"
