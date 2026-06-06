from __future__ import annotations
from typing import Callable, Iterator
from kando.schema.events import KandoEvent, RELATION_CREATED
from kando.world.graph import World


EdgeLogicFn = Callable[[KandoEvent, World], Iterator[KandoEvent]]

_registry: dict[str, EdgeLogicFn] = {}


def edge_logic(relation_type: str):
    """Decorator: fires when a relation of `relation_type` is created."""
    def decorator(fn: EdgeLogicFn) -> EdgeLogicFn:
        _registry[relation_type] = fn
        return fn
    return decorator


def dispatch(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
    if event.type != RELATION_CREATED:
        return
    rel_type = event.data.get("type", "")
    fn = _registry.get(rel_type)
    if fn:
        yield from fn(event, world)
