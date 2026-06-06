# MCP Server

Kando ships a [Model Context Protocol](https://modelcontextprotocol.io/) server that exposes the full agent runtime as tools. Any MCP-compatible host — Claude Desktop, Cursor, Windsurf, or a custom client — can drive Kando directly.

## Starting the server

```bash
kando-mcp
```

The server communicates over stdio (standard MCP transport).

### Configure with Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kando": {
      "command": "kando-mcp",
      "env": {
        "EVENTSTORE_URL": "http://localhost:2113"
      }
    }
  }
}
```

Without `EVENTSTORE_URL`, runs are in-memory (transient). Fork, diff, and trace still work within a single session.

---

## Tools

### `start_run`

Run a Kando kit with a goal. Returns the run ID and world state.

**Input:**

| Parameter | Type | Description |
|---|---|---|
| `kit` | string | Kit name, e.g. `kits.diligence` or `kits/diligence` |
| `goal` | string | Natural-language goal, e.g. `"Evaluate Stripe"` |

**Output:**

```json
{
  "run_id": "abc123def456",
  "ledger": "run:abc123def456",
  "backend": "memory (transient)",
  "event_count": 2,
  "event_ids": ["company.created-abc123", "object.created-1"],
  "objects": [
    {"id": "company-abc123", "type": "Company", "data": {"name": "Stripe"}},
    {"id": "claim-1", "type": "Claim", "data": {...}}
  ],
  "relations": [],
  "note": "In-memory run — set EVENTSTORE_URL to persist..."
}
```

---

### `query_world`

Return the current world state for a run.

**Input:**

| Parameter | Type | Description |
|---|---|---|
| `run_id` | string | Run ID from `start_run` |

**Output:**

```json
{
  "run_id": "abc123def456",
  "event_count": 2,
  "objects": [...],
  "relations": [...]
}
```

!!! note
    Without `EVENTSTORE_URL`, querying a run from a previous session returns an error — in-memory runs are transient.

---

### `fork_run`

Fork an existing run at a ledger position. Returns a new branch ID.

**Input:**

| Parameter | Type | Description |
|---|---|---|
| `run_id` | string | Parent run ID |
| `fork_at` | integer | Ledger position to fork at (0-indexed) |

**Output:**

```json
{
  "branch_id": "789ghi012jkl",
  "parent_run_id": "abc123def456",
  "fork_position": 2,
  "shared_prefix_events": 2
}
```

!!! warning "Requires EventStoreDB"
    `fork_run` requires `EVENTSTORE_URL` to be set.

---

### `diff_branches`

Compare two runs and return a summary of what changed.

**Input:**

| Parameter | Type | Description |
|---|---|---|
| `run_a` | string | Baseline run ID |
| `run_b` | string | Comparison run ID |

**Output:**

```json
{
  "run_a": "abc123def456",
  "run_b": "789ghi012jkl",
  "summary": "+2 objects",
  "added_objects": ["new-claim-id"],
  "removed_objects": [],
  "patched_objects": [],
  "added_relations": [],
  "removed_relations": [],
  "has_changes": true
}
```

!!! warning "Requires EventStoreDB"

---

### `explain_trace`

Return the full causal chain for an event.

**Input:**

| Parameter | Type | Description |
|---|---|---|
| `event_id` | string | Event ID to trace |
| `run_id` | string | Run ID the event belongs to |

**Output:**

```json
{
  "event_id": "claim-1",
  "run_id": "abc123def456",
  "causal_chain": [
    {"id": "claim-1", "type": "object.created", "actor": "diligence.on_company_created", "cause": ["company.created-abc123"], "is_root": false},
    {"id": "company.created-abc123", "type": "object.created", "actor": "cli", "cause": [], "is_root": true}
  ]
}
```
