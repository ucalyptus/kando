# CLI Reference

The `kando` command-line interface provides all operations for running, inspecting, and branching agent runs.

## Installation

```bash
pip install -e ".[stream,mcp]"
kando --help
```

Or without installing (from repo root):

```bash
python -m kando.cli.main --help
```

---

## `kando run`

Run a kit with a goal. Creates a new run ID and executes the kit's responders.

```
kando run <kit> --goal <goal>
```

| Argument | Description |
|---|---|
| `kit` | Kit path. Accepts slash (`kits/diligence`) or dot notation (`kits.diligence`). |
| `--goal` | Natural-language goal for the run (required). |

**Without `EVENTSTORE_URL`:** run is in-memory (transient). Data is lost when the process exits.

**With `EVENTSTORE_URL`:** run is persisted to EventStoreDB. The run ID can be used with `status`, `replay`, `fork`, `diff`, and `trace`.

```bash
# In-memory
kando run kits/diligence --goal "Evaluate Stripe"

# Durable
export EVENTSTORE_URL=http://localhost:2113
kando run kits/diligence --goal "Evaluate Stripe"
# → Run ID  : abc123def456
```

---

## `kando status`

Show the current world state for a run.

```
kando status <run_id>
```

| Argument | Description |
|---|---|
| `run_id` | Run ID from `kando run`. Use `demo` for a built-in in-memory demo. |

```bash
kando status demo
kando status abc123def456
```

---

## `kando replay`

Replay a run from its ledger, reconstructing the world state.

```
kando replay <run_id> [--strict] [--kit <kit>]
```

| Flag | Description |
|---|---|
| `--strict` | Re-fire responders from seed events instead of reprojecting. Verifies determinism. |
| `--kit` | Kit path — required for `--strict` to load responders. |

!!! note "Requires EventStoreDB"
    `replay` needs a durable ledger (`EVENTSTORE_URL` must be set).

```bash
kando replay abc123def456
kando replay abc123def456 --strict --kit kits/diligence
```

---

## `kando fork`

Fork a run at a specific ledger position. Creates a new branch stream.

```
kando fork <run_id> --at <position>
```

| Argument | Description |
|---|---|
| `run_id` | Parent run to fork from. |
| `--at` | Ledger position to fork at (0-indexed, required). |

```bash
kando fork abc123def456 --at 2
# → Branch ID  : 789ghi012jkl
# → Parent run : abc123def456
# → Fork at    : 2  (shared prefix: 2 events)
```

!!! note "Requires EventStoreDB"

---

## `kando diff`

Compare two runs or branches. Shows added/removed/patched objects and relations.

```
kando diff <run_a> <run_b>
```

```bash
kando diff abc123def456 789ghi012jkl
# → Diff: abc123def456 -> 789ghi012jkl
# → Summary: +2 objects, ~1 objects patched
#   + object  new-obj-id  {'type': 'Finding', ...}
```

!!! note "Requires EventStoreDB"

---

## `kando trace`

Show the causal chain for an event — from the event back to the root goal.

```
kando trace <event_id> [--run <run_id>]
```

| Argument | Description |
|---|---|
| `event_id` | ID of the event to trace. |
| `--run` | Run ID the event belongs to. Omit for demo mode. |

```bash
kando trace object.created-2            # demo mode
kando trace claim-1 --run abc123def456  # durable run
```

Output:
```
Causal chain for claim-1:
  claim-1         [object.created]  (cause: ['company.created-abc123'])
  company.created-abc123  [object.created]  (root)
```

---

## `kando-mcp`

Start the MCP stdio server. Used by MCP-compatible hosts like Claude, Cursor, or custom clients.

```bash
kando-mcp
```

See [MCP Server](mcp.md) for details.

---

## Environment variables

| Variable | Description |
|---|---|
| `EVENTSTORE_URL` | EventStoreDB URL, e.g. `http://localhost:2113`. If unset, all runs use the in-memory backend. |
| `KANDO_SNAPSHOT_DIR` | Directory for world snapshots. Default: `.kando_snapshots` in the working directory. |
