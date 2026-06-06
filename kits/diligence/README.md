# Diligence Kit

Reference kit ported from [ActiveGraph](https://github.com/yoheinakajima/activegraph).

Performs structured due-diligence on a company or entity: evidence gathering,
claim extraction, contradiction detection, and synthesis.

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

1. `Company` created → `on_company_created` emits a pending-research `Claim`
2. `Evidence` created (with `claim_id`) → `on_evidence_created` emits `sourced_from` relation
3. `Claim` created (with pre-existing Evidence) → `claim_evidence_linker` emits `supports` relation
4. `Contradiction` created (with `claim_a_id`, `claim_b_id`) → `on_contradiction_created` emits `contradicts` relation
5. `Report` created (with `company_id`) → `on_report_requested` emits `depends_on` relation
