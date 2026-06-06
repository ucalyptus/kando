# Diligence Kit

The diligence kit performs structured due-diligence on a company or entity: evidence gathering, claim extraction, contradiction detection, and synthesis.

## Usage

```bash
kando run kits/diligence --goal "Evaluate Stripe"
```

## Object types

| Type | Description |
|---|---|
| `Company` | The entity under investigation |
| `Claim` | A factual assertion about the company |
| `Evidence` | A piece of evidence supporting or refuting a claim |
| `Contradiction` | A detected conflict between two claims |
| `Report` | A synthesised due-diligence report |

## Relation types

| Type | Direction | Meaning |
|---|---|---|
| `supports` | Evidence → Claim | Evidence backs this claim |
| `contradicts` | Claim → Claim | Two claims are in conflict |
| `depends_on` | Report → Company | Report is about this company |
| `sourced_from` | Evidence → Claim | Evidence is drawn from this claim |

## Responder flow

```
Company created
    │
    ▼ on_company_created
Claim created (pending research)
    │
    ▼ on_evidence_created (when Evidence added)
Relation: sourced_from (Evidence → Claim)
    │
    ▼ claim_evidence_linker (when Claim created with existing Evidence)
Relation: supports (Evidence → Claim)

Contradiction created (claim_a_id + claim_b_id)
    │
    ▼ on_contradiction_created
Relation: contradicts (Claim → Claim)

Report created (company_id)
    │
    ▼ on_report_requested
Relation: depends_on (Report → Company)
```

## Example run

```python
from kando.ledger.memory import MemoryLedgerStore
from kando.runtime import Runtime
from kits.diligence.kit import COMPANY, CLAIM, create_kit, seed_from_goal
from kando.schema.events import KandoEvent, OBJECT_CREATED
from datetime import datetime, timezone

run_id = "example-001"
seed = seed_from_goal("Stripe", run_id)

store = MemoryLedgerStore(run_id)
world = Runtime(ledger=store, responders=create_kit()).run(seed)

# World now has: Company + Claim objects
companies = [o for o in world.objects.values() if o.type == COMPANY]
claims    = [o for o in world.objects.values() if o.type == CLAIM]
```

## Adding Evidence programmatically

```python
from kits.diligence.kit import EVIDENCE

evidence_event = KandoEvent(
    id="evidence-001",
    type=OBJECT_CREATED,
    source=f"run:{run_id}",
    actor="analyst",
    cause=[claims[0].id],
    timestamp=datetime.now(timezone.utc),
    data={
        "id": "evidence-001",
        "type": EVIDENCE,
        "data": {"text": "Stripe processed $1T in 2025", "claim_id": claims[0].id},
    },
)
world = Runtime(ledger=store, responders=create_kit()).run([evidence_event])
# sourced_from relation is now created automatically
```
