"""kando CLI — run, replay, fork, diff, trace, status."""
from __future__ import annotations

import argparse
import importlib
import os
import sys
import uuid
from datetime import datetime, timezone

from kando.ledger.interface import LedgerStore
from kando.ledger.memory import MemoryLedgerStore
from kando.runtime import Runtime
from kando.schema.events import KandoEvent, OBJECT_CREATED, BRANCH_CREATED, make_event
from kando.trace.lineage import build_lineage_index, explain
from kando.world.projection import reproject


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_ledger(run_id: str) -> LedgerStore:
    """Return an ESDB ledger when EVENTSTORE_URL is set, else in-memory."""
    if os.environ.get("EVENTSTORE_URL"):
        from kando.ledger.stream import EventStreamLedgerStore
        return EventStreamLedgerStore(run_id)
    return MemoryLedgerStore(run_id)


def _require_esdb(cmd: str) -> None:
    if not os.environ.get("EVENTSTORE_URL"):
        print(
            f"Error: '{cmd}' requires a durable ledger.\n"
            "Set EVENTSTORE_URL=http://localhost:2113 and start EventStoreDB:\n"
            "  docker compose up -d eventstore",
            file=sys.stderr,
        )
        sys.exit(1)


def _load_kit(kit_path: str):
    """Import a kit module from a path like 'kits/diligence' or 'kits.diligence'."""
    name = kit_path.replace("/", ".").replace("\\", ".").strip(".")
    for candidate in (f"{name}.kit", name, f"kits.{name}.kit", f"kits.{name}"):
        try:
            return importlib.import_module(candidate)
        except ModuleNotFoundError:
            continue
    print(f"Error: cannot find kit at '{kit_path}'.", file=sys.stderr)
    sys.exit(1)


def _new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def _print_world(world, all_events: list) -> None:
    print(f"Events  : {len(all_events)}")
    print(f"Objects : {len(world.objects)}   Relations: {len(world.relations)}")
    for obj in world.objects.values():
        print(f"  [{obj.type:12s}]  {obj.id}  {obj.data}")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_run(args) -> None:
    run_id = _new_run_id()
    kit_mod = _load_kit(args.kit)
    responders = kit_mod.create_kit()
    ledger = _make_ledger(run_id)

    if hasattr(kit_mod, "seed_from_goal"):
        seed_events = list(kit_mod.seed_from_goal(args.goal, run_id))
    else:
        seed_events = [KandoEvent(
            id=f"goal-{run_id[:8]}",
            type=OBJECT_CREATED,
            source=f"run:{run_id}",
            actor="cli",
            cause=[],
            timestamp=datetime.now(timezone.utc),
            data={"id": f"goal-{run_id[:8]}", "type": "Goal", "data": {"goal": args.goal}},
        )]

    world = Runtime(ledger=ledger, responders=responders).run(seed_events)
    all_events = list(ledger.read_all())
    backend = "esdb" if os.environ.get("EVENTSTORE_URL") else "memory (transient)"

    print(f"\nRun ID  : {run_id}")
    print(f"Backend : {backend}")
    print(f"Ledger  : {ledger.stream_name()}")
    print()
    for evt in all_events:
        c = f"<- {evt.cause[0]}" if evt.cause else "(root)"
        print(f"  {evt.id:32s}  [{evt.type}]  {c}")
    print()
    _print_world(world, all_events)

    if not os.environ.get("EVENTSTORE_URL"):
        print("\n  Note: no EVENTSTORE_URL set — run is in-memory only.")
    else:
        print(f"\n  Replay : kando replay {run_id}")
        print(f"  Status : kando status {run_id}")
        print(f"  Trace  : kando trace <event_id> --run {run_id}")


def cmd_status(args) -> None:
    if os.environ.get("EVENTSTORE_URL") and args.run_id != "demo":
        from kando.ledger.stream import EventStreamLedgerStore
        ledger = EventStreamLedgerStore(args.run_id)
        all_events = list(ledger.read_all())
        if not all_events:
            print(f"Run '{args.run_id}' not found in EventStoreDB.", file=sys.stderr)
            sys.exit(1)
    else:
        # Demo mode: seed an in-memory ledger
        ledger = MemoryLedgerStore(args.run_id)
        ts = datetime.now(timezone.utc)
        ledger.append([
            KandoEvent(f"e{i}", OBJECT_CREATED, f"run:{args.run_id}", "demo", [], ts,
                       {"id": f"obj-{i}", "type": "item", "data": {"n": i}})
            for i in range(3)
        ])
        all_events = list(ledger.read_all())

    world = reproject(ledger)
    print(f"Run: {args.run_id}")
    print(f"Events in ledger: {len(all_events)}")
    print(f"Objects in world: {len(world.objects)}")
    print(f"Relations in world: {len(world.relations)}")
    for obj in world.objects.values():
        print(f"  [{obj.type}] {obj.id}  data={obj.data}")


def cmd_replay(args) -> None:
    _require_esdb("replay")
    from kando.ledger.stream import EventStreamLedgerStore
    ledger = EventStreamLedgerStore(args.run_id)
    if args.strict:
        responders = []
        if args.kit:
            kit_mod = _load_kit(args.kit)
            responders = kit_mod.create_kit()
        runtime = Runtime(ledger=ledger, responders=responders)
        world = runtime.replay(strict=True)
    else:
        world = reproject(ledger)
    all_events = list(ledger.read_all())
    mode = "strict" if args.strict else "permissive"
    print(f"Replayed ({mode}): {args.run_id}")
    _print_world(world, all_events)


def cmd_fork(args) -> None:
    _require_esdb("fork")
    from kando.ledger.stream import EventStreamLedgerStore

    branch_id = _new_run_id()
    parent_store = EventStreamLedgerStore(args.run_id)
    branch_store = EventStreamLedgerStore(branch_id)

    # Copy the shared prefix up to fork_position
    prefix = list(parent_store.read(from_position=0))[: args.at]
    if prefix:
        branch_store.append(prefix)

    # Record the branch-creation event in the branch stream
    branch_store.append([KandoEvent(
        id=f"branch.created-{branch_id[:8]}",
        type=BRANCH_CREATED,
        source=f"branch:{branch_id}",
        actor="cli",
        cause=[prefix[-1].id] if prefix else [],
        timestamp=datetime.now(timezone.utc),
        data={
            "branch_id": branch_id,
            "parent_run_id": args.run_id,
            "fork_position": args.at,
        },
    )])

    print(f"Branch ID    : {branch_id}")
    print(f"Parent run   : {args.run_id}")
    print(f"Fork position: {args.at}  (shared prefix: {len(prefix)} events)")
    print(f"\n  Continue: set EVENTSTORE_URL then run  kando status {branch_id}")
    print(f"  Diff    : kando diff {args.run_id} {branch_id}")


def cmd_diff(args) -> None:
    _require_esdb("diff")
    from kando.ledger.stream import EventStreamLedgerStore
    from kando.branch.diff import diff as world_diff

    store_a = EventStreamLedgerStore(args.run_a)
    store_b = EventStreamLedgerStore(args.run_b)
    world_a = reproject(store_a)
    world_b = reproject(store_b)
    d = world_diff(world_a, world_b)

    print(f"Diff: {args.run_a} -> {args.run_b}")
    print(f"Summary: {d.summary()}")
    if d.added_objects:
        for oid in d.added_objects:
            print(f"  + object  {oid}  {world_b.objects[oid].data}")
    if d.removed_objects:
        for oid in d.removed_objects:
            print(f"  - object  {oid}  {world_a.objects[oid].data}")
    if d.patched_objects:
        for oid in d.patched_objects:
            print(f"  ~ object  {oid}  {world_a.objects[oid].data} -> {world_b.objects[oid].data}")
    if d.added_relations:
        print(f"  + relations: {d.added_relations}")
    if d.removed_relations:
        print(f"  - relations: {d.removed_relations}")


def cmd_trace(args) -> None:
    if os.environ.get("EVENTSTORE_URL") and args.run:
        from kando.ledger.stream import EventStreamLedgerStore
        store = EventStreamLedgerStore(args.run)
    else:
        # Demo mode
        store = MemoryLedgerStore("demo")
        e0 = make_event(OBJECT_CREATED, "run:demo", "cli", [], {"id": "root", "type": "goal", "data": {}}, 0)
        e1 = make_event(OBJECT_CREATED, "run:demo", "cli", [e0.id], {"id": "step1", "type": "task", "data": {}}, 1)
        e2 = make_event(OBJECT_CREATED, "run:demo", "cli", [e1.id], {"id": "step2", "type": "task", "data": {}}, 2)
        store.append([e0, e1, e2])

    all_events = list(store.read_all())
    index = build_lineage_index(all_events)

    if args.event_id not in index:
        print(f"Event '{args.event_id}' not found. Available: {list(index.keys())}")
        sys.exit(1)

    chain = explain(args.event_id, all_events)
    print(f"Causal chain for {args.event_id}:")
    for evt in chain:
        cause_str = f"  (cause: {evt.cause})" if evt.cause else "  (root)"
        print(f"  {evt.id} [{evt.type}]{cause_str}")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kando",
        description="Production runtime for long-running agents.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run a kit with a goal")
    p_run.add_argument("kit", help="Kit path, e.g. kits/diligence")
    p_run.add_argument("--goal", required=True, help="Natural-language goal for the run")
    p_run.set_defaults(fn=cmd_run)

    p_replay = sub.add_parser("replay", help="Replay a run from its ledger")
    p_replay.add_argument("run_id", help="Run ID to replay")
    p_replay.add_argument("--strict", action="store_true",
                          help="Re-fire responders instead of reprojecting")
    p_replay.add_argument("--kit", default=None,
                          help="Kit path to load responders for strict replay (e.g. kits/diligence)")
    p_replay.set_defaults(fn=cmd_replay)

    p_fork = sub.add_parser("fork", help="Fork a run at a specific ledger position")
    p_fork.add_argument("run_id", help="Run ID to fork from")
    p_fork.add_argument("--at", type=int, required=True,
                        help="Position to fork at (0-indexed)")
    p_fork.set_defaults(fn=cmd_fork)

    p_diff = sub.add_parser("diff", help="Diff two runs or branches")
    p_diff.add_argument("run_a", help="First run ID")
    p_diff.add_argument("run_b", help="Second run ID")
    p_diff.set_defaults(fn=cmd_diff)

    p_trace = sub.add_parser("trace", help="Trace the causal chain of an event")
    p_trace.add_argument("event_id", help="Event ID to trace")
    p_trace.add_argument("--run", default=None, metavar="RUN_ID",
                         help="Run ID to load events from (uses demo if omitted)")
    p_trace.set_defaults(fn=cmd_trace)

    p_status = sub.add_parser("status", help="Show world state for a run")
    p_status.add_argument("run_id", help="Run ID (use 'demo' for in-memory demo)")
    p_status.set_defaults(fn=cmd_status)

    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
