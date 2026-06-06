from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Iterator
from kando.schema.events import KandoEvent
from kando.world.graph import World


ResponderFn = Callable[[KandoEvent, World], Iterator[KandoEvent]]


@dataclass
class Responder:
    name: str
    pattern: frozenset[str]
    fn: ResponderFn

    def matches(self, event: KandoEvent) -> bool:
        return not self.pattern or event.type in self.pattern

    def handle(self, event: KandoEvent, world: World) -> Iterator[KandoEvent]:
        yield from self.fn(event, world)


class ResponderRegistry:
    """Maintains a collection of responders and dispatches events to matching ones."""

    def __init__(self) -> None:
        self._responders: list[Responder] = []

    def register(self, r: Responder) -> None:
        self._responders.append(r)

    def matching(self, event: KandoEvent) -> list[Responder]:
        return [r for r in self._responders if r.matches(event)]

    def responder(self, name: str, pattern: str | list[str]):
        """Decorator: registers the decorated function as a named responder."""
        def dec(fn: ResponderFn) -> Responder:
            normalized = frozenset({pattern} if isinstance(pattern, str) else pattern)
            r = Responder(name=name, pattern=normalized, fn=fn)
            self.register(r)
            return r
        return dec


def responder(name: str, pattern: str | set[str]):
    """Module-level decorator for one-off responder construction (no registry)."""
    def decorator(fn: ResponderFn) -> Responder:
        normalized = frozenset({pattern} if isinstance(pattern, str) else pattern)
        return Responder(name=name, pattern=normalized, fn=fn)
    return decorator
