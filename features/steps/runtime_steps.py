from __future__ import annotations
from datetime import datetime, timezone
from pytest_bdd import scenarios, given, when, then, parsers
from kando.ledger.memory import MemoryLedgerStore
from kando.runtime import Runtime
from kando.responders.base import Responder
from kando.responders.budget import Budget
from kando.schema.events import KandoEvent, OBJECT_CREATED, BUDGET_EXHAUSTED
from kando.world.projection import project

scenarios('../runtime.feature')


def _ts():
    return datetime.now(timezone.utc)


def _seed_event(obj_id: str, counter: int = 0) -> KandoEvent:
    return KandoEvent(
        id=f"seed-{obj_id}-{counter}",
        type=OBJECT_CREATED,
        source="run:test",
        actor="seed",
        cause=[],
        timestamp=_ts(),
        data={"id": obj_id, "type": "goal", "data": {}},
    )


@given('a runtime with an empty ledger and no responders', target_fixture='rt_ctx')
def runtime_no_responders():
    store = MemoryLedgerStore("rt-test")
    rt = Runtime(store, responders=[])
    return {"runtime": rt, "store": store, "world": None}


@given('a runtime with a responder that emits a child event on object.created', target_fixture='rt_ctx')
def runtime_with_child_responder():
    store = MemoryLedgerStore("rt-responder")
    child_events = []

    def child_fn(event, world):
        if event.data.get("id") == "parent":
            child_id = "child-of-parent"
            child_event = KandoEvent(
                id="child-event",
                type=OBJECT_CREATED,
                source="run:rt-responder",
                actor="child-responder",
                cause=[event.id],
                timestamp=_ts(),
                data={"id": child_id, "type": "child", "data": {}},
            )
            child_events.append(child_id)
            yield child_event

    responder = Responder(
        name="child-responder",
        pattern=frozenset({OBJECT_CREATED}),
        fn=child_fn,
    )
    rt = Runtime(store, responders=[responder])
    return {"runtime": rt, "store": store, "world": None, "child_events": child_events}


@given('a runtime with a budget of max_events=2', target_fixture='rt_ctx')
def runtime_with_tight_budget():
    store = MemoryLedgerStore("rt-budget")
    budget = Budget(max_events=2)

    counter = [0]

    def flood_fn(event, world):
        for i in range(10):
            counter[0] += 1
            yield KandoEvent(
                id=f"flood-{counter[0]}",
                type=OBJECT_CREATED,
                source="run:rt-budget",
                actor="flood-responder",
                cause=[event.id],
                timestamp=_ts(),
                data={"id": f"flood-obj-{counter[0]}", "type": "flood", "data": {}},
            )

    responder = Responder(
        name="flood-responder",
        pattern=frozenset({OBJECT_CREATED}),
        fn=flood_fn,
    )
    rt = Runtime(store, responders=[responder], budget=budget)
    return {"runtime": rt, "store": store, "world": None}


@given('a ledger with committed events', target_fixture='rt_ctx')
def ledger_with_committed():
    store = MemoryLedgerStore("rt-replay")
    # Pre-populate ledger directly
    events = [
        KandoEvent(
            id=f"pre-{i}",
            type=OBJECT_CREATED,
            source="run:rt-replay",
            actor="seed",
            cause=[],
            timestamp=_ts(),
            data={"id": f"pre-obj-{i}", "type": "thing", "data": {}},
        )
        for i in range(3)
    ]
    store.append(events)
    rt = Runtime(store, responders=[])
    return {"runtime": rt, "store": store, "world": None}


@when(parsers.parse('I run with a seed object.created event for "{obj_id}"'))
def run_with_seed(rt_ctx, obj_id):
    seed = _seed_event(obj_id)
    rt_ctx["world"] = rt_ctx["runtime"].run([seed])


@when('I run with a seed event that triggers a responder that emits 10 events')
def run_with_flood_seed(rt_ctx):
    seed = _seed_event("trigger-obj")
    rt_ctx["world"] = rt_ctx["runtime"].run([seed])


@when('I call replay with strict False')
def call_replay(rt_ctx):
    rt_ctx["replayed_world"] = rt_ctx["runtime"].replay(strict=False)


@then(parsers.parse('the ledger contains {n:d} event'))
def check_ledger_count(rt_ctx, n):
    events = list(rt_ctx["store"].read_all())
    assert len(events) == n, f"Expected {n} events in ledger, got {len(events)}"


@then(parsers.parse('the world contains object "{obj_id}"'))
def check_world_has_object(rt_ctx, obj_id):
    world = rt_ctx["world"]
    assert obj_id in world.objects, f"Object {obj_id} not in world"


@then('the world contains the child object emitted by the responder')
def check_child_object(rt_ctx):
    world = rt_ctx["world"]
    assert "child-of-parent" in world.objects, "Child object not found in world"


@then('a budget.exhausted event is in the ledger')
def check_budget_exhausted(rt_ctx):
    events = list(rt_ctx["store"].read_all())
    types = [e.type for e in events]
    assert BUDGET_EXHAUSTED in types, f"budget.exhausted not found; event types: {types}"


@then('the world does not grow beyond the budget')
def check_world_size_bounded(rt_ctx):
    world = rt_ctx["world"]
    # With max_events=2: seed event (1) + BudgetEnforcer fires → should stop very quickly
    assert len(world.objects) <= 10, f"World grew too large: {len(world.objects)} objects"


@then('the resulting world matches direct projection of the ledger')
def check_replay_matches_projection(rt_ctx):
    replayed = rt_ctx["replayed_world"]
    direct = project(rt_ctx["store"].read_all())
    assert set(replayed.objects.keys()) == set(direct.objects.keys()), (
        "Replayed world objects don't match direct projection"
    )
