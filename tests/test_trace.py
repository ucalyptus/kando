"""Tests for lineage: causal order and explain returns event objects."""
import pytest
from datetime import datetime, timezone
from kando.schema.events import KandoEvent, OBJECT_CREATED
from kando.trace.lineage import build_lineage_index, trace, explain


def ts():
    return datetime.now(timezone.utc)


def evt(id: str, cause: list[str]) -> KandoEvent:
    return KandoEvent(
        id=id, type=OBJECT_CREATED, source="run:t", actor="t",
        cause=cause, timestamp=ts(), data={"id": id, "type": "x", "data": {}},
    )


# ---------------------------------------------------------------------------
# trace() returns IDs in causal order
# ---------------------------------------------------------------------------

def test_trace_single_chain():
    events = [evt("e1", []), evt("e2", ["e1"]), evt("e3", ["e2"])]
    index = build_lineage_index(events)
    chain = trace("e3", index)
    assert chain[0] == "e3"
    assert "e2" in chain
    assert "e1" in chain


def test_trace_root_event():
    events = [evt("root", [])]
    index = build_lineage_index(events)
    chain = trace("root", index)
    assert chain == ["root"]


def test_trace_stops_at_root():
    events = [evt("a", []), evt("b", ["a"]), evt("c", ["b"])]
    index = build_lineage_index(events)
    chain = trace("c", index)
    assert len(chain) == 3
    assert chain[-1] == "a"


def test_trace_unknown_id_returns_single_element():
    events = [evt("a", [])]
    index = build_lineage_index(events)
    chain = trace("unknown", index)
    assert chain == ["unknown"]


# ---------------------------------------------------------------------------
# explain() returns KandoEvent objects
# ---------------------------------------------------------------------------

def test_explain_returns_event_objects():
    events = [evt("e1", []), evt("e2", ["e1"]), evt("e3", ["e2"])]
    chain = explain("e3", events)
    assert all(isinstance(e, KandoEvent) for e in chain)


def test_explain_first_element_is_target():
    events = [evt("root", []), evt("mid", ["root"]), evt("leaf", ["mid"])]
    chain = explain("leaf", events)
    assert chain[0].id == "leaf"


def test_explain_includes_all_ancestors():
    events = [evt("root", []), evt("mid", ["root"]), evt("leaf", ["mid"])]
    chain = explain("leaf", events)
    ids = [e.id for e in chain]
    assert "root" in ids
    assert "mid" in ids
    assert "leaf" in ids


def test_explain_root_only():
    events = [evt("root", [])]
    chain = explain("root", events)
    assert len(chain) == 1
    assert chain[0].id == "root"


def test_explain_filters_unknown_parents():
    """Parents not present in the events list are silently dropped."""
    events = [evt("orphan", ["ghost-parent"])]
    chain = explain("orphan", events)
    ids = [e.id for e in chain]
    assert "orphan" in ids
    assert "ghost-parent" not in ids
