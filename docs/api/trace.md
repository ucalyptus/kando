# Trace & Lineage

Every event records its causal ancestors in the `cause` field. The trace module reconstructs the full causal chain from any event back to the root goal.

## Functions

::: kando.trace.lineage.build_lineage_index
    options:
      show_source: true
      heading_level: 3

::: kando.trace.lineage.explain
    options:
      show_source: true
      heading_level: 3

::: kando.trace.lineage.trace
    options:
      show_source: true
      heading_level: 3

---

## Usage

```python
from kando.trace.lineage import build_lineage_index, explain

all_events = list(store.read_all())

# Full causal chain as event objects, from target back to root
chain = explain("claim-1", all_events)
for evt in chain:
    cause_str = f"← {evt.cause}" if evt.cause else "(root)"
    print(f"  {evt.id} [{evt.type}] actor={evt.actor} {cause_str}")
```

Output:
```
  claim-1 [object.created] actor=diligence.on_company_created ← ['company.created-abc123']
  company.created-abc123 [object.created] actor=cli (root)
```

## Reading from the CLI

```bash
kando trace claim-1 --run abc123def456
```

## Via MCP

```json
{
  "tool": "explain_trace",
  "arguments": {"event_id": "claim-1", "run_id": "abc123def456"}
}
```

## Design note

Traces are not observability bolted on after the fact — they are a structural output of every run. The `cause` list on every event is written at emission time by each responder, so the lineage graph is always complete and queryable without additional instrumentation.
