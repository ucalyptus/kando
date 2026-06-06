from __future__ import annotations
from typing import Callable, Iterator
from kando.schema.events import KandoEvent
from kando.world.graph import World


ResponderFn = Callable[[KandoEvent, World], Iterator[KandoEvent]]


class Responder:
    def __init__(self, name: str, pattern: str | set[str], fn: ResponderFn) -> None:
        self.name = name
        self.pattern = {pattern} if isinstance(pattern, str) else set(pattern)
        self._fn = fn

    def matches(self, event: KandoEvent) -> bool:
        return event.type in self.pattern

    def handle(self, event: KandoEvent, world: World) -> Iterator[KandoEvent]:
        yield from self._fn(event, world)


def responder(name: str, pattern: str | set[str]):
    """Decorator: @responder('name', 'event.type')"""
    def decorator(fn: ResponderFn) -> Responder:
        return Responder(name=name, pattern=pattern, fn=fn)
    return decorator
