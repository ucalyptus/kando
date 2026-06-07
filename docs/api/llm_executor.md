# LLM Executor

The LLM executor is a pluggable responder that handles `llm.request` events by calling a user-supplied LLM function, then emits `llm.response` events with the result.

## LLMExecutorResponder

::: kando.responders.llm_executor.LLMExecutorResponder
    options:
      show_source: true
      heading_level: 3

---

## LLMFn signature

```python
LLMFn = Callable[[list[dict], str, int], tuple[str, float]]
#                  messages   model max_tokens  -> (text, cost_usd)
```

The function receives:

| Parameter | Type | Description |
|---|---|---|
| `messages` | `list[dict]` | Chat messages (OpenAI/Anthropic format) |
| `model` | `str` | Model identifier from the `llm.request` event |
| `max_tokens` | `int` | Max response tokens |

It must return a `(response_text, cost_usd)` tuple.

---

## Built-in implementations

### Anthropic

Uses the Anthropic SDK directly. Activated when `ANTHROPIC_API_KEY` is set.

```python
from kando.responders.anthropic_llm import anthropic_llm
from kando.responders.llm_executor import LLMExecutorResponder

responders = create_kit() + [LLMExecutorResponder(anthropic_llm)]
```

### OpenRouter

Routes through the OpenRouter API. Activated when `OPENROUTER_API_KEY` is set (takes priority over Anthropic).

```python
from kando.responders.openrouter_llm import openrouter_llm
from kando.responders.llm_executor import LLMExecutorResponder

responders = create_kit() + [LLMExecutorResponder(openrouter_llm)]
```

Set `OPENROUTER_MODEL` to override the default model (`anthropic/claude-haiku-4-5`).

---

## Usage

```python
from kando.responders.llm_executor import LLMExecutorResponder

# Custom LLM function
def my_llm(messages: list[dict], model: str, max_tokens: int) -> tuple[str, float]:
    # Call your LLM provider
    response = call_api(messages=messages, model=model, max_tokens=max_tokens)
    return response.text, response.cost

responders = create_kit() + [LLMExecutorResponder(my_llm)]
runtime = Runtime(ledger=store, responders=responders)
world = runtime.run(seed)
```

## Caching

The executor checks `world.context["cache"]` (an `LLMCache`) before calling the LLM function. If a cached response exists for the same `(messages, model, max_tokens)` triple, it is served without an API call. New responses are written to the cache automatically.

## How the CLI wires it

When you run `kando run`, the CLI auto-attaches an `LLMExecutorResponder` if an API key is available:

1. `OPENROUTER_API_KEY` → uses `openrouter_llm`
2. `ANTHROPIC_API_KEY` → uses `anthropic_llm`
3. Neither set → no executor attached; `llm.request` events are logged but unanswered
