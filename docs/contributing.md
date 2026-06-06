# Contributing

## Development setup

```bash
git clone https://github.com/ucalyptus/kando.git
cd kando
make dev-setup
make test
```

## Running tests

```bash
make test                    # full suite (pytest)
make test ARGS="-k budget"   # filter by name
```

The test suite uses:

- `pytest` — unit and integration tests
- `hypothesis` — property-based tests
- `pytest-bdd` — Gherkin feature specs

All 159 tests run in under 2 seconds without any external services.

## Test patterns

### Unit test with MemoryLedgerStore

```python
def test_my_responder():
    store = MemoryLedgerStore("test-run")
    world = Runtime(ledger=store, responders=[my_responder]).run([seed_event])
    assert "expected-obj" in world.objects
```

### BDD feature test

Feature files live in `features/`. Steps are in `features/steps/`.

```gherkin
# features/mykit.feature
Feature: My Kit

  Scenario: Goal creates questions
    Given a fresh run with the research kit
    When I run the goal "Understand AI"
    Then the world has at least 3 Question objects
```

### Property-based test

```python
from hypothesis import given, strategies as st
from kando.cache.llm import LLMCache

@given(st.dictionaries(st.text(), st.text()))
def test_cache_roundtrip(request):
    cache = LLMCache()
    cache.put(request, "response")
    assert cache.get(request) == "response"
```

## Adding a kit

1. Create `kits/<name>/__init__.py` and `kits/<name>/kit.py`
2. Export `create_kit() -> list[Responder]`
3. Optionally export `seed_from_goal(goal, run_id) -> list[KandoEvent]`
4. Add tests in `tests/test_<name>_kit.py`
5. Add documentation in `docs/kits/<name>.md`
6. Add to `docs/kits/index.md` table
7. Add to `mkdocs.yml` nav

See [Writing a Kit](kits/authoring.md) for the full pattern.

## Building the docs

```bash
make docs         # build HTML to site/
make docs-serve   # live-reload dev server on http://localhost:8000
```

## Code style

- No type: ignore comments
- No bare `except` clauses
- Default to no comments — only add when the WHY is non-obvious
- No backwards-compatibility hacks for unused code — delete it

## Commit messages

Follow the existing style:

```
Short summary (imperative, ≤72 chars)

Longer explanation of what changed and why (not what — the diff shows that).
Reference the design principle if relevant.

Co-Authored-By: ...
```

## PR checklist

- [ ] Tests pass: `make test`
- [ ] New behaviour has tests
- [ ] Docs updated if public API changed
- [ ] No backwards-compatibility shims for removed code
