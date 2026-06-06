# Kits

A **kit** is a domain bundle: object types, responders, edge logic, and seed logic packaged for a specific use case.

## Included kits

| Kit | Goal | Objects | Relations |
|---|---|---|---|
| [Diligence](diligence.md) | Due-diligence on a company or entity | Company, Claim, Evidence, Contradiction, Report | supports, contradicts, depends_on, sourced_from |
| [Research](research.md) | Decompose a topic into questions, findings, and synthesis | Goal, Question, Source, Finding, Synthesis | decomposes_into, answers, synthesizes, cites |

## Kit interface

Every kit module must export:

```python
def create_kit() -> list[Responder]:
    """Return the list of responders for this kit."""
    ...
```

Optionally, a kit can export:

```python
def seed_from_goal(goal: str, run_id: str) -> list[KandoEvent]:
    """Convert a free-text goal into seed events for this kit."""
    ...
```

If `seed_from_goal` is absent, the CLI wraps the goal text in a generic `Goal` object event.

## Kit discovery

Kits are loaded by name using Python's import machinery. The loader tries these candidates in order:

```
{name}.kit
{name}
kits.{name}.kit
kits.{name}
```

So `kits/diligence`, `kits.diligence`, `kits.diligence.kit` all resolve to the same module.

## Running a kit

```bash
kando run kits/diligence --goal "Evaluate Stripe"
kando run kits/research  --goal "Understand quantum computing"
```

## Authoring a kit

→ [Writing a Kit](authoring.md)
