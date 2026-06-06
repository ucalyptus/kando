"""LLM executor responder: reads llm.request events, calls a pluggable LLM function,
emits llm.response. No business logic — callers own the prompt and the response handling."""
from __future__ import annotations

from typing import Callable, Iterator

from kando.responders.base import Responder
from kando.schema.events import KandoEvent, LLM_REQUEST, LLM_RESPONSE, make_event
from kando.world.graph import World

# (messages, model, max_tokens) -> (response_text, cost_usd)
LLMFn = Callable[[list[dict], str, int], tuple[str, float]]


def _make_executor_fn(llm_fn: LLMFn):
    def _handle(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
        messages = event.data.get("messages", [])
        model = event.data.get("model", "claude-haiku-4-5-20251001")
        max_tokens = event.data.get("max_tokens", 1024)
        cause_object_id = event.data.get("cause_object_id", "")

        cache = world.context.get("cache")
        cache_request = {"messages": messages, "model": model, "max_tokens": max_tokens}

        cached = cache.get(cache_request) if cache else None
        if cached is not None:
            text, cost_usd = cached
        else:
            text, cost_usd = llm_fn(messages, model, max_tokens)
            if cache:
                cache.put(cache_request, (text, cost_usd))

        yield make_event(
            type=LLM_RESPONSE,
            source=event.source,
            actor="llm_executor",
            cause=[event.id],
            data={
                "text": text,
                "model": model,
                "cost_usd": cost_usd,
                "cause_object_id": cause_object_id,
            },
        )

    return _handle


def LLMExecutorResponder(llm_fn: LLMFn) -> Responder:
    """Factory: returns a Responder that calls llm_fn for every llm.request event.

    Usage:
        def my_llm(messages, model, max_tokens):
            ...  # call Anthropic/OpenAI/etc
            return response_text, cost_usd

        responders = create_kit() + [LLMExecutorResponder(my_llm)]
    """
    return Responder(
        name="llm_executor",
        pattern=frozenset({LLM_REQUEST}),
        fn=_make_executor_fn(llm_fn),
    )
