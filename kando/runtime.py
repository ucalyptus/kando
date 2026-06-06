from __future__ import annotations
from typing import Iterator
from kando.ledger.interface import LedgerStore
from kando.world.graph import World
from kando.world.projection import project, apply
from kando.responders.base import Responder
from kando.responders.budget import Budget, BudgetEnforcer
from kando.schema.events import KandoEvent, BUDGET_EXHAUSTED


class Runtime:
    def __init__(
        self,
        ledger: LedgerStore,
        responders: list[Responder],
        budget: Budget | None = None,
    ) -> None:
        self._ledger    = ledger
        self._responders = responders
        self._budget_enforcer = BudgetEnforcer(
            budget or Budget(),
            run_id=ledger.stream_name(),
        )

    def load(self) -> World:
        return project(self._ledger.read_all())

    def run(self, seed_events: list[KandoEvent]) -> World:
        world = self.load()
        queue = list(seed_events)

        while queue:
            event = queue.pop(0)
            self._ledger.append([event])
            apply(world, event)

            # budget check
            for exhaust in self._budget_enforcer.check(event, world):
                self._ledger.append([exhaust])
                return world

            if event.type == BUDGET_EXHAUSTED:
                return world

            # fire matching responders
            for r in self._responders:
                if r.matches(event):
                    for new_event in r.handle(event, world):
                        queue.append(new_event)

        return world

    def replay(self, strict: bool = False) -> World:
        """Reconstruct world from ledger. strict=True re-fires responders."""
        if not strict:
            return self.load()
        raise NotImplementedError("Strict replay not yet implemented")
