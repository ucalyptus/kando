"""Tests for budget wall-clock and recursion-depth enforcement."""
from __future__ import annotations

import time
from datetime import datetime, timezone

import pytest

from kando.ledger.memory import MemoryLedgerStore
from kando.responders.base import Responder
from kando.responders.budget import Budget, BudgetEnforcer
from kando.runtime import Runtime
from kando.schema.events import KandoEvent, OBJECT_CREATED, BUDGET_EXHAUSTED, make_event
from kando.world.graph import World


def _ts():
    return datetime.now(timezone.utc)


def _evt(eid: str, cause: list[str] | None = None) -> KandoEvent:
    return KandoEvent(eid, OBJECT_CREATED, "run:t", "test", cause or [], _ts(),
                      {"id": eid, "type": "x", "data": {}})


class _FakeWorld(World):
    pass


def _enforcer(budget: Budget) -> BudgetEnforcer:
    return BudgetEnforcer(budget, run_id="test")


# ---------------------------------------------------------------------------
# Wall-clock limit
# ---------------------------------------------------------------------------

def test_wall_clock_not_triggered_immediately():
    e = _enforcer(Budget(max_wall_seconds=60.0))
    e.record(_evt("e0"), _FakeWorld())
    assert e.violations(_evt("e0")) == []


def test_wall_clock_triggers_when_exceeded(monkeypatch):
    e = _enforcer(Budget(max_wall_seconds=1.0))
    # Simulate 2 seconds elapsed
    e._start_time -= 2.0
    ev = _evt("e1")
    e.record(ev, _FakeWorld())
    events = e.violations(ev)
    assert len(events) == 1
    assert events[0].type == BUDGET_EXHAUSTED
    reasons = events[0].data["reasons"]
    assert any("max_wall_seconds" in r for r in reasons)


# ---------------------------------------------------------------------------
# Recursion depth limit
# ---------------------------------------------------------------------------

def test_recursion_depth_zero_for_root_event():
    e = _enforcer(Budget(max_recursion_depth=10))
    e.record(_evt("root"), _FakeWorld())
    assert e._depths["root"] == 0


def test_recursion_depth_increments_with_cause():
    e = _enforcer(Budget(max_recursion_depth=10))
    e.record(_evt("e0"), _FakeWorld())
    e.record(_evt("e1", ["e0"]), _FakeWorld())
    e.record(_evt("e2", ["e1"]), _FakeWorld())
    assert e._depths["e0"] == 0
    assert e._depths["e1"] == 1
    assert e._depths["e2"] == 2


def test_recursion_depth_triggers_budget_exhausted():
    e = _enforcer(Budget(max_recursion_depth=2))
    e.record(_evt("e0"), _FakeWorld())
    e.record(_evt("e1", ["e0"]), _FakeWorld())
    ev2 = _evt("e2", ["e1"])
    e.record(ev2, _FakeWorld())
    events = e.violations(ev2)
    assert len(events) == 1
    assert events[0].type == BUDGET_EXHAUSTED
    assert any("max_recursion_depth" in r for r in events[0].data["reasons"])


def test_recursion_depth_uses_max_of_multiple_causes():
    e = _enforcer(Budget(max_recursion_depth=10))
    e.record(_evt("a"), _FakeWorld())      # depth 0
    e.record(_evt("b", ["a"]), _FakeWorld())  # depth 1
    e.record(_evt("c", ["a"]), _FakeWorld())  # depth 1
    e.record(_evt("d", ["b", "c"]), _FakeWorld())  # depth 2 (max(1,1)+1)
    assert e._depths["d"] == 2


# ---------------------------------------------------------------------------
# Runtime integration: depth limit stops the loop
# ---------------------------------------------------------------------------

def _chain_responder(event: KandoEvent, world: World):
    """Always emit one more event, causing infinite chain without budget."""
    n = event.data.get("n", 0)
    yield KandoEvent(
        id=f"chain-{n + 1}", type=OBJECT_CREATED,
        source=event.source, actor="chain-responder",
        cause=[event.id], timestamp=_ts(),
        data={"id": f"obj-{n+1}", "type": "node", "data": {"n": n + 1}},
    )


def test_runtime_depth_limit_stops_infinite_chain():
    store = MemoryLedgerStore("depth-budget-test")
    responders = [Responder(name="chain", pattern=frozenset({OBJECT_CREATED}), fn=_chain_responder)]
    runtime = Runtime(
        ledger=store,
        responders=responders,
        budget=Budget(max_recursion_depth=5, max_events=1000),
    )
    seed = KandoEvent("seed-0", OBJECT_CREATED, "run:t", "cli", [], _ts(),
                      {"id": "obj-0", "type": "node", "data": {"n": 0}})
    world = runtime.run([seed])
    all_events = list(store.read_all())
    # Should have stopped well before 1000 events
    assert len(all_events) < 20
    exhausted = [e for e in all_events if e.type == BUDGET_EXHAUSTED]
    assert len(exhausted) == 1


# ---------------------------------------------------------------------------
# Memory-leak regression: _depths must stay bounded
# ---------------------------------------------------------------------------

def test_depths_bounded():
    """BudgetEnforcer._depths must not grow without bound."""
    budget = Budget(max_events=10_000, max_recursion_depth=50)
    enforcer = BudgetEnforcer(budget, run_id="test")
    world = _FakeWorld()

    # Build a 2000-event linear chain
    prev_id = None
    for i in range(2000):
        event = make_event(
            type="object.created",
            source="run:test",
            actor="test",
            cause=[prev_id] if prev_id else [],
            data={"id": f"obj-{i}", "type": "test"},
        )
        enforcer.record(event, world)
        prev_id = event.id

    # _depths should be bounded by max_recursion_depth * 4, not 2000
    assert len(enforcer._depths) <= budget.max_recursion_depth * 5, \
        f"_depths has {len(enforcer._depths)} entries — memory leak"


def test_record_increments_even_without_violations():
    """record() must always increment _event_count, independent of violations()."""
    enforcer = BudgetEnforcer(Budget(max_events=100), run_id="test")
    world = World()
    event = make_event(type=OBJECT_CREATED, source="run:test", actor="test",
                       cause=[], data={"id": "obj-1", "type": "test"})
    enforcer.record(event, world)
    assert enforcer._event_count == 1
    # violations() should return empty (well under limit)
    assert enforcer.violations(event) == []
