"""Kando MCP server — exposes agent runtime over the Model Context Protocol."""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from kando.ledger.interface import LedgerStore
from kando.ledger.memory import MemoryLedgerStore
from kando.runtime import Runtime
from kando.schema.events import KandoEvent, OBJECT_CREATED, BRANCH_CREATED
from kando.trace.lineage import build_lineage_index, explain
from kando.world.projection import reproject
from kando.branch.diff import diff as world_diff

server = Server("kando")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ledger(run_id: str) -> LedgerStore:
    if os.environ.get("EVENTSTORE_URL"):
        from kando.ledger.stream import EventStreamLedgerStore
        return EventStreamLedgerStore(run_id)
    return MemoryLedgerStore(run_id)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]



def _run_kit(kit_name: str, goal: str) -> tuple[str, dict]:
    """Synchronously run a kit and return (run_id, result_dict)."""
    import importlib
    run_id = _new_id()

    name = kit_name.replace("/", ".").replace("\\", ".").strip(".")
    for candidate in (f"{name}.kit", name, f"kits.{name}.kit", f"kits.{name}"):
        try:
            kit_mod = importlib.import_module(candidate)
            break
        except ModuleNotFoundError:
            continue
    else:
        raise ValueError(f"Kit '{kit_name}' not found")

    responders = kit_mod.create_kit()
    ledger = _make_ledger(run_id)

    if hasattr(kit_mod, "seed_from_goal"):
        seed_events = list(kit_mod.seed_from_goal(goal, run_id))
    else:
        seed_events = [KandoEvent(
            id=f"goal-{run_id[:8]}",
            type=OBJECT_CREATED,
            source=f"run:{run_id}",
            actor="mcp",
            cause=[],
            timestamp=datetime.now(timezone.utc),
            data={"id": f"goal-{run_id[:8]}", "type": "Goal", "data": {"goal": goal}},
        )]

    world = Runtime(ledger=ledger, responders=responders).run(seed_events)
    all_events = list(ledger.read_all())

    durable = bool(os.environ.get("EVENTSTORE_URL"))
    return run_id, {
        "run_id": run_id,
        "ledger": ledger.stream_name(),
        "backend": "esdb" if durable else "memory (transient)",
        "event_count": len(all_events),
        "event_ids": [e.id for e in all_events],
        "objects": [{"id": o.id, "type": o.type, "data": o.data} for o in world.objects.values()],
        "relations": list(world.relations.keys()),
        "note": None if durable else "In-memory run — set EVENTSTORE_URL to persist and enable trace/fork/diff.",
    }


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS = [
    types.Tool(
        name="start_run",
        description=(
            "Run a Kando kit with a goal. Returns run_id and the resulting world state "
            "(objects and relations). Use the run_id to replay, fork, diff, or trace later."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "kit": {
                    "type": "string",
                    "description": "Kit name, e.g. 'kits.diligence' or 'kits/diligence'",
                },
                "goal": {
                    "type": "string",
                    "description": "Natural-language goal for the run, e.g. 'Evaluate Stripe'",
                },
            },
            "required": ["kit", "goal"],
        },
    ),
    types.Tool(
        name="query_world",
        description=(
            "Return the current world state (all objects and relations) for a run. "
            "Requires EVENTSTORE_URL to be set for durable runs."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "Run ID returned by start_run"},
            },
            "required": ["run_id"],
        },
    ),
    types.Tool(
        name="fork_run",
        description=(
            "Fork an existing run at a specific ledger position. Returns a new branch_id. "
            "The branch shares the event prefix up to fork_at; new events diverge from there."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "Parent run ID"},
                "fork_at": {
                    "type": "integer",
                    "description": "Ledger position to fork at (0-indexed). Use query_world to see event count.",
                },
            },
            "required": ["run_id", "fork_at"],
        },
    ),
    types.Tool(
        name="diff_branches",
        description=(
            "Compare two runs or branches and return a summary of what changed: "
            "added/removed/patched objects and added/removed relations."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "run_a": {"type": "string", "description": "First run ID (baseline)"},
                "run_b": {"type": "string", "description": "Second run ID (comparison)"},
            },
            "required": ["run_a", "run_b"],
        },
    ),
    types.Tool(
        name="explain_trace",
        description=(
            "Return the full causal chain for an event — from the event back to the root goal. "
            "Shows which responder emitted each event and what caused it."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "Event ID to trace"},
                "run_id": {"type": "string", "description": "Run ID the event belongs to"},
            },
            "required": ["event_id", "run_id"],
        },
    ),
]


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        result = await asyncio.get_running_loop().run_in_executor(
            None, _dispatch, name, arguments
        )
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as exc:
        return [types.TextContent(type="text", text=json.dumps({"error": str(exc)}))]


# ---------------------------------------------------------------------------
# Synchronous dispatch (runs in executor)
# ---------------------------------------------------------------------------

def _dispatch(name: str, args: dict) -> dict:
    if name == "start_run":
        try:
            _, result = _run_kit(args["kit"], args["goal"])
        except (ValueError, ModuleNotFoundError) as exc:
            return {"error": str(exc)}
        return result

    if name == "query_world":
        run_id = args["run_id"]
        ledger = _make_ledger(run_id)
        all_events = list(ledger.read_all())
        if not all_events and not os.environ.get("EVENTSTORE_URL"):
            return {"error": f"Run '{run_id}' not found. Set EVENTSTORE_URL for durable runs."}
        world = reproject(ledger)
        return {
            "run_id": run_id,
            "event_count": len(all_events),
            "objects": [{"id": o.id, "type": o.type, "data": o.data} for o in world.objects.values()],
            "relations": list(world.relations.keys()),
        }

    if name == "fork_run":
        if not os.environ.get("EVENTSTORE_URL"):
            return {"error": "fork_run requires EVENTSTORE_URL (durable ledger)."}
        from kando.ledger.stream import EventStreamLedgerStore
        run_id, fork_at = args["run_id"], int(args["fork_at"])
        branch_id = _new_id()
        parent = EventStreamLedgerStore(run_id)
        branch = EventStreamLedgerStore(branch_id)
        prefix = list(parent.read(from_position=0))[:fork_at]
        if prefix:
            branch.append(prefix)
        branch.append([KandoEvent(
            id=f"branch.created-{branch_id[:8]}",
            type=BRANCH_CREATED,
            source=f"branch:{branch_id}",
            actor="mcp",
            cause=[prefix[-1].id] if prefix else [],
            timestamp=datetime.now(timezone.utc),
            data={"branch_id": branch_id, "parent_run_id": run_id, "fork_position": fork_at},
        )])
        return {
            "branch_id": branch_id,
            "parent_run_id": run_id,
            "fork_position": fork_at,
            "shared_prefix_events": len(prefix),
        }

    if name == "diff_branches":
        if not os.environ.get("EVENTSTORE_URL"):
            return {"error": "diff_branches requires EVENTSTORE_URL (durable ledger)."}
        from kando.ledger.stream import EventStreamLedgerStore
        run_a, run_b = args["run_a"], args["run_b"]
        world_a = reproject(EventStreamLedgerStore(run_a))
        world_b = reproject(EventStreamLedgerStore(run_b))
        d = world_diff(world_a, world_b)
        return {
            "run_a": run_a,
            "run_b": run_b,
            "summary": d.summary(),
            "added_objects": d.added_objects,
            "removed_objects": d.removed_objects,
            "patched_objects": d.patched_objects,
            "added_relations": d.added_relations,
            "removed_relations": d.removed_relations,
            "has_changes": bool(d),
        }

    if name == "explain_trace":
        run_id, event_id = args["run_id"], args["event_id"]
        ledger = _make_ledger(run_id)
        all_events = list(ledger.read_all())
        index = build_lineage_index(all_events)
        if event_id not in index:
            return {
                "error": f"Event '{event_id}' not found in run '{run_id}'.",
                "available_events": list(index.keys()),
            }
        chain = explain(event_id, all_events)
        return {
            "event_id": event_id,
            "run_id": run_id,
            "causal_chain": [
                {
                    "id": evt.id,
                    "type": evt.type,
                    "actor": evt.actor,
                    "cause": evt.cause,
                    "is_root": not bool(evt.cause),
                }
                for evt in chain
            ],
        }

    return {"error": f"Unknown tool: {name}"}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def _serve() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    """Entry point for the kando-mcp console script."""
    asyncio.run(_serve())


if __name__ == "__main__":
    main()
