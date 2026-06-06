"""Tests for MCP server dispatch layer (synchronous, no stdio)."""
from __future__ import annotations

import sys
import os
import pytest
from datetime import datetime, timezone

from kando.mcp.server import _dispatch, _run_kit


# ---------------------------------------------------------------------------
# start_run — in-memory diligence run
# ---------------------------------------------------------------------------

def test_start_run_returns_run_id_and_objects():
    result = _dispatch("start_run", {"kit": "kits.diligence", "goal": "Acme Corp"})
    assert "run_id" in result
    assert isinstance(result["event_ids"], list)
    assert len(result["event_ids"]) >= 1
    assert isinstance(result["objects"], list)
    obj_types = {o["type"] for o in result["objects"]}
    # Diligence kit creates Company and a Claim
    assert "Company" in obj_types


def test_start_run_memory_note_present_without_esdb(monkeypatch):
    monkeypatch.delenv("EVENTSTORE_URL", raising=False)
    result = _dispatch("start_run", {"kit": "kits.diligence", "goal": "Test"})
    assert result["backend"] == "memory (transient)"
    assert result["note"] is not None


def test_start_run_invalid_kit_returns_error():
    result = _dispatch("start_run", {"kit": "kits.nonexistent_kit_xyz", "goal": "Test"})
    assert "error" in result


# ---------------------------------------------------------------------------
# query_world — memory ledger has no persistence across calls
# ---------------------------------------------------------------------------

def test_query_world_unknown_run_returns_error(monkeypatch):
    monkeypatch.delenv("EVENTSTORE_URL", raising=False)
    result = _dispatch("query_world", {"run_id": "deadbeef000000"})
    assert "error" in result


# ---------------------------------------------------------------------------
# fork_run — requires ESDB, returns error without it
# ---------------------------------------------------------------------------

def test_fork_run_without_esdb_returns_error(monkeypatch):
    monkeypatch.delenv("EVENTSTORE_URL", raising=False)
    result = _dispatch("fork_run", {"run_id": "abc", "fork_at": 0})
    assert "error" in result
    assert "EVENTSTORE_URL" in result["error"]


# ---------------------------------------------------------------------------
# diff_branches — requires ESDB
# ---------------------------------------------------------------------------

def test_diff_branches_without_esdb_returns_error(monkeypatch):
    monkeypatch.delenv("EVENTSTORE_URL", raising=False)
    result = _dispatch("diff_branches", {"run_a": "abc", "run_b": "def"})
    assert "error" in result


# ---------------------------------------------------------------------------
# explain_trace — works in memory
# ---------------------------------------------------------------------------

def test_explain_trace_finds_root_event(monkeypatch):
    monkeypatch.delenv("EVENTSTORE_URL", raising=False)
    # First run a kit to get real events in a ledger
    # We'll test against a manually set up ledger
    from kando.ledger.memory import MemoryLedgerStore
    from kando.runtime import Runtime
    from kando.schema.events import KandoEvent, OBJECT_CREATED

    run_id = "trace-test-001"
    ledger = MemoryLedgerStore(run_id)
    seed = KandoEvent(
        "seed-evt", OBJECT_CREATED, f"run:{run_id}", "cli", [],
        datetime.now(timezone.utc),
        {"id": "obj-root", "type": "Goal", "data": {"goal": "test"}},
    )
    Runtime(ledger=ledger, responders=[]).run([seed])

    # Monkeypatch _make_ledger to return our pre-populated ledger
    import kando.mcp.server as mcp_mod
    original = mcp_mod._make_ledger
    mcp_mod._make_ledger = lambda _run_id: ledger
    try:
        result = _dispatch("explain_trace", {"event_id": "seed-evt", "run_id": run_id})
    finally:
        mcp_mod._make_ledger = original

    assert "causal_chain" in result
    chain = result["causal_chain"]
    assert len(chain) >= 1
    root = chain[0]
    assert root["id"] == "seed-evt"
    assert root["is_root"] is True


def test_explain_trace_unknown_event_returns_error(monkeypatch):
    monkeypatch.delenv("EVENTSTORE_URL", raising=False)
    from kando.ledger.memory import MemoryLedgerStore
    import kando.mcp.server as mcp_mod
    run_id = "empty-trace-run"
    ledger = MemoryLedgerStore(run_id)
    original = mcp_mod._make_ledger
    mcp_mod._make_ledger = lambda _: ledger
    try:
        result = _dispatch("explain_trace", {"event_id": "ghost-event", "run_id": run_id})
    finally:
        mcp_mod._make_ledger = original
    assert "error" in result


# ---------------------------------------------------------------------------
# Unknown tool
# ---------------------------------------------------------------------------

def test_unknown_tool_returns_error():
    result = _dispatch("not_a_real_tool", {})
    assert "error" in result
    assert "not_a_real_tool" in result["error"]
