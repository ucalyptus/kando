"""Event delivery bus: subscribe callbacks to event patterns and deliver events to them."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterator

from kando.responders.base import Responder
from kando.schema.events import KandoEvent
from kando.world.graph import World


Callback = Callable[[KandoEvent], None]


@dataclass
class Subscription:
    name: str
    pattern: frozenset[str]   # event types to match; empty set matches ALL types
    callback: Callback


class DeliveryBus:
    """In-process subscriber registry. Thread-safety is the caller's responsibility."""

    def __init__(self) -> None:
        self._subscriptions: list[Subscription] = []

    def subscribe(
        self,
        callback: Callback,
        name: str,
        pattern: frozenset[str] | set[str] | None = None,
    ) -> None:
        """Register a callback.

        Args:
            callback: callable(event) called synchronously on each matching event.
            name: unique name for this subscription (used in delivery receipts).
            pattern: set of event type strings to match. None / empty matches all types.
        """
        self._subscriptions.append(Subscription(
            name=name,
            pattern=frozenset(pattern) if pattern else frozenset(),
            callback=callback,
        ))

    def unsubscribe(self, name: str) -> bool:
        """Remove a subscription by name. Returns True if it existed."""
        before = len(self._subscriptions)
        self._subscriptions = [s for s in self._subscriptions if s.name != name]
        return len(self._subscriptions) < before

    def deliver(self, event: KandoEvent) -> list[str]:
        """Dispatch event to all matching subscribers. Returns list of reached subscriber names."""
        reached: list[str] = []
        for sub in self._subscriptions:
            if not sub.pattern or event.type in sub.pattern:
                sub.callback(event)
                reached.append(sub.name)
        return reached

    def __len__(self) -> int:
        return len(self._subscriptions)


def create_delivery_responder(bus: DeliveryBus) -> Responder:
    """Return a Responder that delivers every event to the given bus.

    Usage::

        bus = DeliveryBus()
        bus.subscribe(my_webhook_fn, name="webhook", pattern={"run.completed"})
        runtime = Runtime(ledger=..., responders=[..., create_delivery_responder(bus)])
    """
    def _deliver(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
        bus.deliver(event)
        return iter([])

    return Responder(
        name="delivery.bus",
        pattern=frozenset(),   # empty = match all event types
        fn=_deliver,
    )
