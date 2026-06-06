from __future__ import annotations
from collections import deque
from kando.ledger.interface import LedgerStore
from kando.world.graph import World
from kando.world.projection import project, apply, reproject
from kando.responders.base import Responder
from kando.responders.budget import Budget, BudgetEnforcer
from kando.responders import edge as edge_logic
from kando.schema.events import KandoEvent, BUDGET_EXHAUSTED


class Runtime:
    """Wires ledger, world projection, responders, and budget into a single event loop.

    Fails loudly on responder errors — never swallows exceptions.
    """

    def __init__(
        self,
        ledger: LedgerStore,
        responders: list[Responder],
        budget: Budget | None = None,
    ) -> None:
        self._ledger = ledger
        self._responders = responders
        self._budget_enforcer = BudgetEnforcer(
            budget or Budget(),
            run_id=ledger.stream_name(),
        )

    def load(self) -> World:
        """Reconstruct the current world from the ledger."""
        return reproject(self._ledger)

    def run(self, seed_events: list[KandoEvent]) -> World:
        """Main event loop: process seed events, fire responders, exhaust the queue."""
        world = self.load()
        queue: deque[KandoEvent] = deque(seed_events)

        while queue:
            event = queue.popleft()
            self._ledger.append([event])
            apply(world, event)

            if self._handle_budget(event, world):
                return world

            if event.type == BUDGET_EXHAUSTED:
                return world

            self._dispatch(event, world, queue)

        return world

    def _handle_budget(self, event: KandoEvent, world: World) -> bool:
        """Check budget and commit exhaustion event if needed. Returns True if exhausted."""
        exhaust_event = self._check_budget(event, world)
        if exhaust_event is not None:
            self._ledger.append([exhaust_event])
            return True
        return False

    def _dispatch(self, event: KandoEvent, world: World, queue: deque) -> None:
        """Dispatch event to edge logic and all matching responders, enqueuing outputs."""
        for new_event in edge_logic.dispatch(event, world):
            queue.append(new_event)
        for r in self._responders:
            if r.matches(event):
                for new_event in r.handle(event, world):
                    queue.append(new_event)

    def replay(self, strict: bool = False) -> World:
        """Permissive replay: reproject ledger. Strict mode raises NotImplementedError."""
        if strict:
            raise NotImplementedError("Strict replay not yet implemented")
        return self.load()

    def _check_budget(self, event: KandoEvent, world: World) -> KandoEvent | None:
        """Return a budget-exhausted event if limits are hit, else None."""
        for exhaust in self._budget_enforcer.check(event, world):
            return exhaust
        return None
