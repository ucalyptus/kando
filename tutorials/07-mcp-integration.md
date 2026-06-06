# Tutorial 7 — MCP Integration

**BLUF: Run `kando-mcp` and any MCP-compatible host (Claude Desktop,
Cursor, VS Code) can start runs, query worlds, fork branches, diff
outcomes, and trace causality — all through five tool calls.**

---

## Why this matters

MCP (Model Context Protocol) lets AI assistants call external tools. By
exposing Kando as an MCP server, you give any compatible host the ability
to run structured agent workflows — not just chat, but event-sourced
runs with full traceability.

---

## Step 1 — Start the MCP server

```bash
kando-mcp
```

This starts a stdio-based MCP server. It's meant to be launched by a host
application, not run interactively.

## Step 2 — Configure your MCP host

### Claude Desktop

Add to your Claude Desktop MCP config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "kando": {
      "command": "/path/to/kando/.venv/bin/kando-mcp",
      "env": {
        "EVENTSTORE_URL": "http://localhost:2113"
      }
    }
  }
}
```

### Cursor / VS Code

Add to your editor's MCP settings the equivalent command configuration
pointing to `kando-mcp`.

---

## The five tools

| Tool | What it does | Requires ESDB? |
|---|---|---|
| `start_run` | Run a kit with a goal, returns run_id + world state | No (in-memory OK) |
| `query_world` | Return current objects and relations for a run | Yes |
| `fork_run` | Fork a run at a ledger position, returns branch_id | Yes |
| `diff_branches` | Compare two runs/branches structurally | Yes |
| `explain_trace` | Causal chain from any event back to the root | Yes |

### start_run

```json
{
  "kit": "kits/diligence",
  "goal": "Evaluate Stripe"
}
```

Returns:

```json
{
  "run_id": "a1b2c3d4e5f6",
  "event_count": 5,
  "objects": [
    {"id": "company-a1b2c3d4", "type": "Company", "data": {"name": "Evaluate Stripe"}},
    {"id": "claim-ef567890", "type": "Claim", "data": {"text": "...", "status": "pending"}}
  ],
  "relations": ["rel-sourced-11223344"]
}
```

### query_world

```json
{"run_id": "a1b2c3d4e5f6"}
```

Returns the same objects/relations structure for an existing run.

### fork_run

```json
{"run_id": "a1b2c3d4e5f6", "fork_at": 2}
```

Returns:

```json
{
  "branch_id": "x9y8z7w6v5u4",
  "parent_run_id": "a1b2c3d4e5f6",
  "fork_position": 2,
  "shared_prefix_events": 2
}
```

### diff_branches

```json
{"run_a": "a1b2c3d4e5f6", "run_b": "x9y8z7w6v5u4"}
```

Returns added/removed/patched objects and relations.

### explain_trace

```json
{"event_id": "object.patched-a1b2c3d4", "run_id": "a1b2c3d4e5f6"}
```

Returns the full causal chain as a list of events from root to target.

---

## Example conversation with Claude

Once configured, you can say to Claude:

> "Run a diligence check on Stripe and trace how the main claim was produced."

Claude will:

1. Call `start_run` with `kit: "kits/diligence"`, `goal: "Evaluate Stripe"`
2. Read the returned objects, find the Claim event ID
3. Call `explain_trace` with that event ID
4. Explain the full causal chain to you

All of this happens through structured tool calls — not prompt engineering,
not text parsing.

---

## Key takeaways

- `kando-mcp` exposes five tools over the Model Context Protocol.
- Any MCP host can run kits, query state, fork, diff, and trace.
- In-memory mode works for `start_run`; durable mode (ESDB) required for
  the rest.
- The MCP server is the bridge between conversational AI and structured
  event-sourced agent runs.

---

**You've completed all tutorials.** For reference material, see the
[docs/](../docs/) directory or run `kando --help`.
