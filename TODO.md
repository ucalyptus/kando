# Kando — Gap List (from architecture grill)

## 1. Wire up the LLM executor (most critical)

The runtime has `llm.request` and `llm.response` event types defined but no responder
that actually calls an LLM. All findings are `[Pending]` placeholders.

### Steps

**1a. Extend `schema/events.py`** — ensure `LLM_REQUEST` / `LLM_RESPONSE` payloads are
documented/typed:
```python
# LLM_REQUEST payload shape
{
  "messages": [{"role": "user", "content": "..."}],
  "model": "claude-haiku-4-5-20251001",
  "max_tokens": 1024,
  "cause_object_id": "<id of the object this is answering>"
}
# LLM_RESPONSE payload shape
{
  "text": "...",
  "model": "...",
  "cost_usd": 0.002,
  "cause_object_id": "<echoed from request>"
}
```

**1b. Update `_on_question_created` in `kits/research/kit.py`** — instead of emitting a
`[Pending]` Finding directly, emit an `LLM_REQUEST` event with the question as the prompt.

**1c. Add `LLMExecutorResponder`** — a responder that listens on `llm.request`, calls the
API (start with Anthropic SDK), emits `llm.response`. Executor is dumb: no business logic,
just call and emit.

**1d. Add `_on_llm_response` responder in the research kit** — listens on `llm.response`,
reads `cause_object_id`, emits `OBJECT_CREATED` with real `text` and `status: "complete"`
(same ID as the pending Finding — projection overwrites by last-write-wins).

## 2. Do the same for `kits/diligence/kit.py`

Diligence has `[Pending research for <company>]` Claims with no real research behind them.
Same pattern: emit `LLM_REQUEST` from `_on_company_created`, handle response to fill the
Claim.

## 3. Verify projection handles duplicate OBJECT_CREATED cleanly

`apply()` already does last-write-wins (confirmed). Add a test that explicitly checks:
emit OBJECT_CREATED id=X with `status: pending`, then OBJECT_CREATED id=X with
`status: complete` — world should reflect the second.

## 4. Consider `OBJECT_PATCHED` over re-emit for finding updates

`OBJECT_PATCHED` is already implemented in `projection.py`. For the LLM response handler,
using `OBJECT_PATCHED` (patch `{text, status}` onto the existing pending Finding) is
cleaner than a second `OBJECT_CREATED` because it preserves the original creation event.
Decision deferred — either works.

## 5. Default model decision

Pick a default model for the executor. Recommendation: `claude-haiku-4-5-20251001`
(fast, cheap, good for structured extraction). Override per-request via the `model` field
in `LLM_REQUEST`.

## Parking lot (grill questions not yet reached)

- Should the executor responder be in `kando/responders/` (core) or kit-level?
- Multi-agent / concurrent run safety (ESAA paper concern)
- Hash-verified replay (ESAA requirement — not implemented)
- Schema/boundary contracts on responder output (ESAA requirement — not implemented)
