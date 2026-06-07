# Research Kit

The research kit decomposes a goal into sub-questions, generates placeholder findings for each, and synthesises them into a structured summary.

## Usage

```bash
kando run kits/research --goal "Understand AI safety"
```

## Object types

| Type | Description |
|---|---|
| `Goal` | The top-level research objective |
| `Question` | A sub-question derived from the goal |
| `Source` | A reference or citation for a finding |
| `Finding` | An answer or insight for a question |
| `Synthesis` | A summary derived from all findings |

## Relation types

| Type | Direction | Meaning |
|---|---|---|
| `decomposes_into` | Goal → Question | The goal is broken into this question |
| `answers` | Finding → Question | This finding addresses the question |
| `synthesizes` | Synthesis → Goal | Synthesis summarises the goal's findings |
| `cites` | Finding → Source | Finding is backed by this source |

## Responder flow

```
Goal created
    │
    ▼ on_goal_created
3 × Question created
    + 3 × decomposes_into relations (Goal → Question)
    │
    ▼ on_question_created (fires for each Question)
3 × Finding created (status: "pending")
    + 3 × answers relations (Finding → Question)
    │
    ├─▶ on_pending_finding_created (fires for each pending Finding)
    │   3 × llm.request events emitted
    │       │
    │       ▼ LLMExecutorResponder (if ANTHROPIC_API_KEY or OPENROUTER_API_KEY set)
    │       3 × llm.response events
    │           │
    │           ▼ on_llm_response (patches each Finding with LLM text)
    │           3 × object.patched events (status → "complete")
    │               │
    │               ▼ on_finding_patched (when all findings are complete)
    │               1 × object.patched on Synthesis (summary filled in)
    │
    ▼ on_finding_created (when all questions have findings)
1 × Synthesis created (status: "pending")
    + 1 × synthesizes relation (Synthesis → Goal)
```

!!! info "Without an LLM API key"
    When no `ANTHROPIC_API_KEY` or `OPENROUTER_API_KEY` is set, the `llm.request` events
    are written to the ledger but no executor fires. Findings and synthesis remain in
    `"pending"` status. You can attach your own `LLMExecutorResponder` to fill them in.

## Default decomposition

When a goal is created, `on_goal_created` emits three questions by default:

1. `What are the key facts about: {goal}?`
2. `What are the main risks or challenges for: {goal}?`
3. `What evidence supports or refutes claims about: {goal}?`

These can be replaced by a custom responder that generates questions via LLM.

## Example run

```python
from kando.ledger.memory import MemoryLedgerStore
from kando.runtime import Runtime
from kits.research.kit import GOAL, QUESTION, FINDING, SYNTHESIS, create_kit, seed_from_goal

run_id = "research-001"
seed = seed_from_goal("Quantum computing adoption", run_id)

store = MemoryLedgerStore(run_id)
world = Runtime(ledger=store, responders=create_kit()).run(seed)

goals      = [o for o in world.objects.values() if o.type == GOAL]       # 1
questions  = [o for o in world.objects.values() if o.type == QUESTION]   # 3
findings   = [o for o in world.objects.values() if o.type == FINDING]    # 3
syntheses  = [o for o in world.objects.values() if o.type == SYNTHESIS]  # 1
```

## Extending with LLM responders

Replace the placeholder finding responder with one that calls an LLM:

```python
from kando.responders.base import Responder
from kando.schema.events import KandoEvent, OBJECT_CREATED, make_event
from kando.world.graph import World
from kits.research.kit import QUESTION, FINDING, ANSWERS, create_kit

def _llm_answer(event: KandoEvent, world: World):
    if event.data.get("type") != QUESTION:
        return
    cache = world.context.get("cache")
    q_text = event.data["data"]["text"]
    # ... call LLM, use cache.get/put for deduplication
    finding_id = f"llm-finding-{event.id}"
    yield make_event(
        type=OBJECT_CREATED, source=event.source,
        actor="llm-researcher", cause=[event.id],
        data={"id": finding_id, "type": FINDING,
              "data": {"text": "...", "question_id": event.data["id"]}},
    )

llm_responder = Responder(
    name="research.llm_answerer",
    pattern=frozenset({OBJECT_CREATED}),
    fn=_llm_answer,
)
# Replace the default on_question_created with this
```
