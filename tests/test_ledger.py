"""Store parity: memory vs stream backends."""
import pytest
from datetime import datetime, timezone
from kando.ledger.memory import MemoryLedgerStore
from kando.schema.events import KandoEvent, OBJECT_CREATED


def make_event(i: int) -> KandoEvent:
    return KandoEvent(
        id=f"evt-{i}",
        type=OBJECT_CREATED,
        source="run:test",
        actor="test",
        cause=[],
        timestamp=datetime.now(timezone.utc),
        data={"id": f"obj-{i}", "type": "thing", "data": {}},
    )


def test_memory_append_and_read():
    store = MemoryLedgerStore("test-run")
    events = [make_event(i) for i in range(5)]
    store.append(events)
    result = list(store.read_all())
    assert len(result) == 5
    assert result[0].id == "evt-0"


def test_memory_read_from_position():
    store = MemoryLedgerStore("test-run")
    store.append([make_event(i) for i in range(10)])
    result = list(store.read(from_position=5))
    assert len(result) == 5
    assert result[0].id == "evt-5"


def test_stream_name():
    store = MemoryLedgerStore("abc-123")
    assert store.stream_name() == "run:abc-123"
