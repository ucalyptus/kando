from __future__ import annotations
from datetime import datetime, timezone
from pytest_bdd import scenarios, given, when, then, parsers
from kando.trace.lineage import build_lineage_index, trace, explain
from kando.schema.events import KandoEvent, OBJECT_CREATED

scenarios('../trace.feature')


def _ts():
    return datetime.now(timezone.utc)


def _make_event(eid: str, cause: list) -> KandoEvent:
    return KandoEvent(
        id=eid,
        type=OBJECT_CREATED,
        source="run:trace-test",
        actor="test",
        cause=cause,
        timestamp=_ts(),
        data={"id": eid, "type": "thing", "data": {}},
    )


@given('a ledger with root event "e0" child "e1" caused by "e0" grandchild "e2" caused by "e1"',
       target_fixture='trace_ctx')
def three_event_chain():
    e0 = _make_event("e0", [])
    e1 = _make_event("e1", ["e0"])
    e2 = _make_event("e2", ["e1"])
    events = [e0, e1, e2]
    index = build_lineage_index(events)
    return {"events": events, "index": index, "chain": None, "result": None}


@given('a ledger with root event "e0" with no causes', target_fixture='trace_ctx')
def single_root_event():
    e0 = _make_event("e0", [])
    events = [e0]
    index = build_lineage_index(events)
    return {"events": events, "index": index, "chain": None, "result": None}


@given('a chain of events e0 then e1 caused by e0 then e2 caused by e1', target_fixture='trace_ctx')
def chain_for_explain():
    e0 = _make_event("e0", [])
    e1 = _make_event("e1", ["e0"])
    e2 = _make_event("e2", ["e1"])
    events = [e0, e1, e2]
    return {"events": events, "index": build_lineage_index(events), "chain": None, "result": None}


@when(parsers.parse('I trace event "{event_id}"'))
def do_trace(trace_ctx, event_id):
    trace_ctx["chain"] = trace(event_id, trace_ctx["index"])


@when(parsers.parse('I call explain for "{event_id}"'))
def do_explain(trace_ctx, event_id):
    trace_ctx["result"] = explain(event_id, trace_ctx["events"])


@then(parsers.parse('the chain contains "{e0}" "{e1}" "{e2}" in that order'))
def check_chain_order(trace_ctx, e0, e1, e2):
    chain = trace_ctx["chain"]
    assert chain == [e0, e1, e2], f"Expected [{e0}, {e1}, {e2}], got {chain}"


@then(parsers.parse('the chain contains only "{eid}"'))
def check_chain_single(trace_ctx, eid):
    chain = trace_ctx["chain"]
    assert chain == [eid], f"Expected [{eid}], got {chain}"


@then('the result is a list of KandoEvent instances')
def check_result_is_events(trace_ctx):
    result = trace_ctx["result"]
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) > 0, "Result should not be empty"
    for item in result:
        assert isinstance(item, KandoEvent), f"Expected KandoEvent, got {type(item)}"
