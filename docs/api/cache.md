# LLM Cache

Content-addressed cache of LLM responses keyed by normalized request hash. On replay or branch, cached responses are served instead of making new API calls.

## LLMCache

::: kando.cache.llm.LLMCache
    options:
      show_source: true
      heading_level: 3

## ScopedLLMCache

::: kando.cache.llm.ScopedLLMCache
    options:
      show_source: true
      heading_level: 3

---

## Usage

```python
from kando.cache.llm import LLMCache
from kando.runtime import Runtime

cache = LLMCache()
runtime = Runtime(ledger=store, responders=create_kit(), cache=cache)
world = runtime.run(seed)

# Access from a responder via world.context
def my_responder(event, world):
    cache = world.context.get("cache")
    request = {"model": "claude-3", "prompt": "Evaluate Stripe..."}
    cached = cache.get(request)
    if cached:
        response = cached
    else:
        response = call_llm(request)
        cache.put(request, response)
    ...
```

## Scoped cache for branches

When forking a run, create a scoped cache that reads from the parent on miss but writes independently:

```python
from kando.cache.llm import LLMCache

parent_cache = LLMCache()
# ... populate during parent run ...

branch_cache = parent_cache.scope("branch-001")
# branch_cache.get() → checks branch store first, falls back to parent
# branch_cache.put() → writes only to branch store
```

## Key behaviour

- Keys are `SHA-256` of the JSON-serialised request dict (sorted keys, no whitespace)
- The same request always maps to the same key regardless of insertion order
- `get()` returns `None` on miss (not `KeyError`)
- `put()` returns the key string
