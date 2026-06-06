# Quickstart

## Prerequisites

- Python 3.11+
- Git
- Docker (optional — only needed for durable runs with EventStoreDB)

---

## 1. Clone and smoke-test

```bash
git clone https://github.com/ucalyptus/kando.git
cd kando
make start
```

`make start` creates a virtualenv, installs dependencies, and runs two demo checks:

```
.venv/bin/python -m kando.cli.main status demo
.venv/bin/python -m kando.cli.main trace object.created-2
```

Expected output for `status demo`:
```
Run: demo
Events in ledger: 3
Objects in world: 3
Relations in world: 0
  [item] obj-0  data={'n': 0}
  [item] obj-1  data={'n': 1}
  [item] obj-2  data={'n': 2}
```

---

## 2. Run a kit in-memory

No Docker needed. Runs are transient (in-memory), which is perfect for exploration.

=== "Diligence"

    ```bash
    make setup
    kando run kits/diligence --goal "Evaluate Stripe"
    ```

    Output:
    ```
    Run ID  : 7bd27e6bcb8d
    Backend : memory (transient)
    Ledger  : run:7bd27e6bcb8d

      company.created-7bd27e6b   [object.created]  (root)
      object.created-1           [object.created]  <- company.created-7bd27e6b

    Events  : 2
    Objects : 2   Relations: 0
      [Company]  company-7bd27e6b  {'name': 'Evaluate Stripe'}
      [Claim  ]  claim-1  {'text': 'Pending research for Evaluate Stripe', ...}

      Note: no EVENTSTORE_URL set — run is in-memory only.
    ```

=== "Research"

    ```bash
    kando run kits/research --goal "Understand quantum computing"
    ```

    Output:
    ```
    Run ID  : 4afb0b1ce6a6
    Backend : memory (transient)
    ...
    Events  : 15
    Objects : 8   Relations: 7
      [Goal      ]  goal-4afb0b1c  {'text': 'Understand quantum computing'}
      [Question  ]  question-1  {'text': 'What are the key facts about...'}
      [Question  ]  question-3  {'text': 'What are the main risks...'}
      [Question  ]  question-5  {'text': 'What evidence supports...'}
      [Finding   ]  finding-7   {'text': '[Pending] Research needed for...'}
      [Finding   ]  finding-9   {'text': '[Pending] Research needed for...'}
      [Finding   ]  finding-11  {'text': '[Pending] Research needed for...'}
      [Synthesis ]  synthesis-13  {'summary': '[Pending synthesis for...]', ...}
    ```

---

## 3. Durable runs with EventStoreDB

Start the event substrate:

```bash
docker compose up -d eventstore
export EVENTSTORE_URL=http://localhost:2113
```

Run a kit — the run ID is now persisted:

```bash
kando run kits/diligence --goal "Evaluate Acme Corp"
# Run ID  : abc123def456
```

Use the run ID for all follow-up commands:

```bash
kando status abc123def456
kando replay abc123def456
kando trace <event_id> --run abc123def456
kando fork  abc123def456 --at 2
kando diff  abc123def456 <branch_id>
```

---

## 4. Install as a package

```bash
pip install -e ".[stream,mcp]"
kando --help
kando-mcp  # start the MCP server
```

---

## 5. Run tests

```bash
make dev-setup
make test
# 159 passed
```

---

## Next steps

- [CLI Reference](cli.md) — all commands and flags
- [MCP Server](mcp.md) — integrate with Claude, Cursor, or any MCP host
- [Kits](kits/index.md) — use or author domain kits
- [Concepts](concepts.md) — understand the event model
