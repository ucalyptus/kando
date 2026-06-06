# Tutorial 5 — Tracing Causality

**BLUF: Every event records the event that caused it. Run
`kando trace <event_id>` and you get the full causal chain from that
event back to the original goal — which responder fired, what triggered
it, and why it exists.**

---

## Why this matters

When an agent produces an artifact — a claim, a finding, a report — you
need to know *why*. Not in a debugging sense bolted on after the fact,
but as structural output that falls out of the architecture for free.

In Kando, every event has a `cause` field: a list of parent event IDs.
Following causes backward gives you a complete lineage from any artifact
to the goal that started it all.

---

## Step 1 — Run a trace (demo mode)

No Docker or API keys needed:

```bash
.venv/bin/python -m kando.cli.main trace object.created-2
```

Output:

```
Causal chain for object.created-2:
  object.created-0 [object.created]  (root)
  object.created-1 [object.created]  (cause: ['object.created-0'])
  object.created-2 [object.created]  (cause: ['object.created-1'])
```

Read it bottom-up: event 2 was caused by event 1, which was caused by
event 0 (the root).

## Step 2 — Trace a real run

With EventStoreDB running:

```bash
export EVENTSTORE_URL=http://localhost:2113
kando run kits/diligence --goal "Evaluate Stripe"
# Note an event ID from the output, e.g. "object.patched-a1b2c3d4"

kando trace object.patched-a1b2c3d4 --run <run_id>
```

You'll see the full chain:

```
Causal chain for object.patched-a1b2c3d4:
  company.created-abcd1234 [object.created]  (root)
  object.created-ef567890 [object.created]  (cause: ['company.created-abcd1234'])
  llm.request-11223344 [llm.request]  (cause: ['object.created-ef567890'])
  llm.response-55667788 [llm.response]  (cause: ['llm.request-11223344'])
  object.patched-a1b2c3d4 [object.patched]  (cause: ['llm.response-55667788'])
```

Read it as a story: the CLI created a Company → which triggered a Claim →
which triggered an LLM request → which got a response → which patched the
Claim with real content.

---

## How it works

### The `cause` field

Every `KandoEvent` has:

```python
cause: list[str]  # parent event IDs
```

When a responder emits a new event, it passes `cause=[event.id]` — linking
the output to the input that triggered it.

### Building the lineage index

```python
from kando.trace.lineage import build_lineage_index, explain

all_events = list(ledger.read_all())
index = build_lineage_index(all_events)  # event_id -> KandoEvent
chain = explain("some-event-id", all_events)  # returns [root, ..., target]
```

`explain()` walks the `cause` links backward until it reaches a root event
(one with `cause=[]`), then returns the chain in chronological order.

---

## What traces tell you

| Question | Answer from the trace |
|---|---|
| Why does this claim exist? | Because a Company was created (root event) |
| Who produced this text? | The `llm.response` event, fired by `LLMExecutorResponder` |
| What triggered the LLM call? | A pending Claim, fired by `diligence.on_pending_claim_created` |
| Can I trust this artifact? | Follow the chain — every step is auditable |

---

## Traces are not observability

This distinction matters. In most systems, traces are a debugging tool
you bolt on with OpenTelemetry or logging. In Kando, the causal chain is
**structural output** — it exists because every event records its parent.
You get it for free, it's always complete, and it's queryable at any time.

---

## Key takeaways

- Every event records `cause` — the event(s) that triggered it.
- `kando trace <event_id>` walks the chain back to the root goal.
- Traces are structural, not a debugging afterthought.
- The lineage index is built from the ledger — no separate tracing system.

---

**Next:** [Tutorial 6 — Building a Kit](06-building-a-kit.md)
