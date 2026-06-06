#!/usr/bin/env python3
"""kando CLI — run, replay, fork, diff, trace, status."""
import argparse, sys


def cmd_run(args):
    print(f"Running kit: {args.kit}")
    raise NotImplementedError


def cmd_replay(args):
    print(f"Replaying run: {args.run_id}")
    raise NotImplementedError


def cmd_fork(args):
    print(f"Forking run {args.run_id} at position {args.at}")
    raise NotImplementedError


def cmd_diff(args):
    print(f"Diffing {args.run_a} vs {args.run_b}")
    raise NotImplementedError


def cmd_trace(args):
    print(f"Tracing event: {args.event_id}")
    raise NotImplementedError


def cmd_status(args):
    print(f"Status for run: {args.run_id}")
    raise NotImplementedError


def main():
    parser = argparse.ArgumentParser(prog="kando")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run a kit")
    p_run.add_argument("kit")
    p_run.add_argument("--goal", required=True)
    p_run.set_defaults(fn=cmd_run)

    p_replay = sub.add_parser("replay", help="Replay a run from ledger")
    p_replay.add_argument("run_id")
    p_replay.add_argument("--strict", action="store_true")
    p_replay.set_defaults(fn=cmd_replay)

    p_fork = sub.add_parser("fork", help="Fork a run at a ledger position")
    p_fork.add_argument("run_id")
    p_fork.add_argument("--at", type=int, required=True)
    p_fork.set_defaults(fn=cmd_fork)

    p_diff = sub.add_parser("diff", help="Diff two runs or branches")
    p_diff.add_argument("run_a")
    p_diff.add_argument("run_b")
    p_diff.set_defaults(fn=cmd_diff)

    p_trace = sub.add_parser("trace", help="Trace causal chain of an event")
    p_trace.add_argument("event_id")
    p_trace.set_defaults(fn=cmd_trace)

    p_status = sub.add_parser("status", help="Show run status")
    p_status.add_argument("run_id")
    p_status.set_defaults(fn=cmd_status)

    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
