from __future__ import annotations
from datetime import datetime, timezone
from pytest_bdd import scenarios, given, when, then, parsers
from kando.ledger.memory import MemoryLedgerStore
from kando.schema.events import KandoEvent, OBJECT_CREATED

scenarios('../ledger.feature')


def _make_event(i: int, run_id: str = "test-run") -> KandoEvent:
    return KandoEvent(
        id=f"evt-{i}",
        type=OBJECT_CREATED,
        source=f"run:{run_id}",
        actor="test",
        cause=[],
        timestamp=datetime.now(timezone.utc),
        data={"id": f"obj-{i}", "type": "thing", "data": {}},
    )


@given('an empty in-memory ledger for run "test-run"', target_fixture='ledger_ctx')
def ledger_test_run():
    return {"store": MemoryLedgerStore("test-run"), "last_pos": None, "read_result": None}


@given('a ledger with 10 events', target_fixture='ledger_ctx')
def ledger_with_10():
    store = MemoryLedgerStore("test-run")
    store.append([_make_event(i) for i in range(10)])
    return {"store": store, "last_pos": None, "read_result": None}


@given(parsers.parse('a ledger for run "{run_id}"'), target_fixture='ledger_ctx')
def ledger_for_run(run_id):
    return {"store": MemoryLedgerStore(run_id), "last_pos": None, "read_result": None}


@when(parsers.parse('I append {n:d} events'))
def append_n_events(ledger_ctx, n):
    events = [_make_event(i) for i in range(n)]
    ledger_ctx["last_pos"] = ledger_ctx["store"].append(events)


@when(parsers.parse('I read from position {pos:d}'))
def read_from_position(ledger_ctx, pos):
    ledger_ctx["read_result"] = list(ledger_ctx["store"].read(from_position=pos))


@then(parsers.parse('the returned position is {pos:d}'))
def check_returned_position(ledger_ctx, pos):
    assert ledger_ctx["last_pos"] == pos, f"Expected position {pos}, got {ledger_ctx['last_pos']}"


@then(parsers.parse('reading all events yields {n:d} events'))
def check_all_events_count(ledger_ctx, n):
    result = list(ledger_ctx["store"].read_all())
    assert len(result) == n, f"Expected {n} events, got {len(result)}"


@then(parsers.parse('I receive exactly {n:d} events'))
def check_read_result_count(ledger_ctx, n):
    assert len(ledger_ctx["read_result"]) == n, (
        f"Expected {n} events, got {len(ledger_ctx['read_result'])}"
    )


@then(parsers.parse('the first event has index {idx:d}'))
def check_first_event_index(ledger_ctx, idx):
    first = ledger_ctx["read_result"][0]
    assert first.id == f"evt-{idx}", f"Expected evt-{idx}, got {first.id}"


@then(parsers.parse('the stream name is "{expected}"'))
def check_stream_name(ledger_ctx, expected):
    assert ledger_ctx["store"].stream_name() == expected
