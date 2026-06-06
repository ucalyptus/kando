"""Store parity: memory backend — position tracking and read semantics."""
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


def test_append_returns_correct_position_single_batch():
    store = MemoryLedgerStore("pos-test")
    pos = store.append([make_event(0), make_event(1), make_event(2)])
    assert pos == 3


def test_append_returns_correct_position_multiple_batches():
    store = MemoryLedgerStore("pos-test")
    pos1 = store.append([make_event(0)])
    assert pos1 == 1
    pos2 = store.append([make_event(1), make_event(2)])
    assert pos2 == 3
    pos3 = store.append([make_event(3)])
    assert pos3 == 4


def test_read_all_after_multiple_appends():
    store = MemoryLedgerStore("multi-append")
    store.append([make_event(0), make_event(1)])
    store.append([make_event(2)])
    store.append([make_event(3), make_event(4)])
    result = list(store.read_all())
    assert len(result) == 5
    assert [e.id for e in result] == ["evt-0", "evt-1", "evt-2", "evt-3", "evt-4"]


def test_append_empty_list_returns_current_position():
    store = MemoryLedgerStore("empty-append")
    store.append([make_event(0)])
    pos = store.append([])
    assert pos == 1
