# Tutorial 1 — Your First Run

**BLUF: Run `kando run kits/diligence --goal "Evaluate Acme Corp"` and you
get an append-only event log, a projected world of objects and relations,
and a causal trace from goal to every artifact — all in one command.**

---

## Why this matters

Most agent frameworks give you a chat transcript. Kando gives you a
structured, replayable, forkable event log. Every object the agent
creates — every claim, every piece of evidence, every relation — is an
event in the ledger. The "world" you see at the end is derived from that
log, never stored directly.

---

## Step 1 — Set up

```bash
git clone https://github.com/ucalyptus/kando.git
cd kando
make setup
```

This creates a `.venv` with all dependencies installed.

## Step 2 — Run the demo status check

No Docker, no API keys, no configuration:

```bash
.venv/bin/python -m kando.cli.main status demo
```

Expected output:

```
Run: demo
Events in ledger: 3
Objects in world: 3
Relations in world: 0
  [item] obj-0  data={'n': 0}
  [item] obj-1  data={'n': 1}
  [item] obj-2  data={'n': 2}
```

**What just happened:** Kando created an in-memory ledger, appended three
`object.created` events, then projected the world (objects + relations)
from that log.

## Step 3 — Run a real kit (in-memory)

```bash
.venv/bin/python -m kando.cli.main run kits/diligence --goal "Evaluate Acme Corp"
```

You will see:

1. A **run ID** (e.g., `a1b2c3d4e5f6`) — the unique identifier for this run.
2. An **event list** — every event the runtime processed, each with its
   type (`object.created`, `relation.created`, `llm.request`, etc.) and
   causal parent.
3. A **world summary** — object count, relation count, and every object
   with its type and data.

Without an `OPENROUTER_API_KEY` or `ANTHROPIC_API_KEY`, LLM-backed
responders produce pending claims but skip the actual API call. That's fine
— the structure is the point.

## Step 4 — Read the output

The output tells you everything:

| Output line | What it means |
|---|---|
| `Run ID: a1b2c3d4e5f6` | Your ledger is named `run:a1b2c3d4e5f6` |
| `Backend: memory (transient)` | Events live in RAM only — they vanish when the process exits |
| `[object.created] (root)` | A seed event with no parent — this is where causality starts |
| `[object.created] <- company.created-a1b2c3d4` | This event was caused by the company creation |
| `[Company] company-a1b2c3d4 {'name': 'Evaluate Acme Corp'}` | A world object projected from the events |

## Step 5 — Try the research kit

```bash
.venv/bin/python -m kando.cli.main run kits/research --goal "Understand AI safety"
```

The research kit decomposes your goal into sub-questions, creates
placeholder findings for each, and (with an LLM key) fills them in and
synthesizes results. Same runtime, different domain vocabulary.

---

## Key takeaways

- **One command** gives you a full event-sourced agent run.
- **No infrastructure required** — in-memory mode works out of the box.
- The ledger is the source of truth; the world is a projection.
- Every event records *what caused it* — traceability is structural, not bolted on.

---

**Next:** [Tutorial 2 — The Ledger Is the Agent](02-ledger-is-the-agent.md)
