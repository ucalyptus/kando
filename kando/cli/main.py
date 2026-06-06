#!/usr/bin/env python3
"""kando CLI — run, replay, fork, diff, trace, status."""
from __future__ import annotations
import argparse
import sys
from datetime import datetime, timezone

from kando.ledger.memory import MemoryLedgerStore
from kando.schema.events import KandoEvent, OBJECT_CREATED, make_event
from kando.trace.lineage import build_lineage_index, trace, explain
from kando.world.projection import reproject


def cmd_run(args):
    print(f"Running kit: {args.kit}  goal: {args.goal}")
    raise NotImplementedError("kit runner not yet wired — use the Python API directly")


def cmd_replay(args):
    print(f"Replaying run: {args.run_id}  strict={args.strict}")
    raise NotImplementedError("durable ledger not yet wired — use MemoryLedgerStore in tests")


def cmd_fork(args):
    print(f"Forking run {args.run_id} at position {args.at}")
    raise NotImplementedError("fork CLI requires durable ledger — not yet implemented")


def cmd_diff(args):
    print(f"Diffing {args.run_a} vs {args.run_b}")
    raise NotImplementedError("diff CLI requires durable ledger — not yet implemented")


def cmd_trace(args):
    """Trace: demo mode builds a small in-memory ledger and prints the causal chain."""
    store = MemoryLedgerStore("demo")
    e0 = make_event(OBJECT_CREATED, "run:demo", "cli", [], {"id": "root", "type": "goal", "data": {}}, 0)
    e1 = make_event(OBJECT_CREATED, "run:demo", "cli", [e0.id], {"id": "step1", "type": "task", "data": {}}, 1)
    e2 = make_event(OBJECT_CREATED, "run:demo", "cli", [e1.id], {"id": "step2", "type": "task", "data": {}}, 2)
    store.append([e0, e1, e2])

    target_id = args.event_id
    all_events = list(store.read_all())
    index = build_lineage_index(all_events)

    if target_id not in index:
        print(f"Event '{target_id}' not found in demo ledger. Available: {list(index.keys())}")
        sys.exit(1)

    chain = explain(target_id, all_events)
    print(f"Causal chain for {target_id}:")
    for evt in chain:
        cause_str = f"  (cause: {evt.cause})" if evt.cause else "  (root)"
        print(f"  {evt.id} [{evt.type}]{cause_str}")


def cmd_status(args):
    """Status: demo mode builds an in-memory ledger and reports world state."""
    store = MemoryLedgerStore(args.run_id)
    ts = datetime.now(timezone.utc)
    events = [
        KandoEvent(f"e{i}", OBJECT_CREATED, f"run:{args.run_id}", "demo", [], ts,
                   {"id": f"obj-{i}", "type": "item", "data": {"n": i}})
        for i in range(3)
    ]
    store.append(events)
    world = reproject(store)

    print(f"Run: {args.run_id}")
    print(f"Events in ledger: {len(list(store.read_all()))}")
    print(f"Objects in world: {len(world.objects)}")
    print(f"Relations in world: {len(world.relations)}")
    for obj in world.objects.values():
        print(f"  [{obj.type}] {obj.id}  data={obj.data}")


def main():
    parser = argparse.ArgumentParser(
        prog="kando",
        description="Production runtime for long-running agents.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run a kit with a goal")
    p_run.add_argument("kit", help="Path to the kit directory or module")
    p_run.add_argument("--goal", required=True, help="Natural-language goal for the run")
    p_run.set_defaults(fn=cmd_run)

    p_replay = sub.add_parser("replay", help="Replay a run from its ledger")
    p_replay.add_argument("run_id", help="Run ID to replay")
    p_replay.add_argument("--strict", action="store_true",
                          help="Re-fire responders instead of just reprojecting")
    p_replay.set_defaults(fn=cmd_replay)

    p_fork = sub.add_parser("fork", help="Fork a run at a specific ledger position")
    p_fork.add_argument("run_id", help="Run ID to fork from")
    p_fork.add_argument("--at", type=int, required=True,
                        help="Ledger position to fork at (prefix is shared)")
    p_fork.set_defaults(fn=cmd_fork)

    p_diff = sub.add_parser("diff", help="Diff two runs or branches")
    p_diff.add_argument("run_a", help="First run or branch ID")
    p_diff.add_argument("run_b", help="Second run or branch ID")
    p_diff.set_defaults(fn=cmd_diff)

    p_trace = sub.add_parser("trace", help="Trace the causal chain of an event")
    p_trace.add_argument("event_id", help="Event ID to trace back to root")
    p_trace.set_defaults(fn=cmd_trace)

    p_status = sub.add_parser("status", help="Show current world state for a run")
    p_status.add_argument("run_id", help="Run ID to inspect")
    p_status.set_defaults(fn=cmd_status)

    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
