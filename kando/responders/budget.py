from __future__ import annotations
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator
from kando.schema.events import KandoEvent, BUDGET_EXHAUSTED
from kando.world.graph import World


@dataclass
class Budget:
    max_events: int = 10_000
    max_llm_cost_usd: float = 10.0
    max_wall_seconds: float = 3600.0
    max_recursion_depth: int = 50


class BudgetEnforcer:
    """Tracks cumulative usage and emits budget.exhausted when limits are hit."""

    def __init__(self, budget: Budget, run_id: str) -> None:
        self._budget = budget
        self._run_id = run_id
        self._event_count = 0
        self._llm_cost = 0.0
        self._start_time = time.monotonic()
        self._depths: dict[str, int] = {}

    def check(self, event: KandoEvent, world: World) -> Iterator[KandoEvent]:
        self._event_count += 1
        if event.type == "llm.response":
            self._llm_cost += event.data.get("cost_usd", 0.0)

        # Track causal depth
        if event.cause:
            depth = max(self._depths.get(c, 0) for c in event.cause) + 1
        else:
            depth = 0
        self._depths[event.id] = depth
        # Prune entries that can never be referenced again as a cause
        if len(self._depths) > self._budget.max_recursion_depth * 4:
            cutoff = depth - self._budget.max_recursion_depth
            self._depths = {k: v for k, v in self._depths.items() if v >= cutoff}

        elapsed = time.monotonic() - self._start_time

        reasons = []
        if self._event_count >= self._budget.max_events:
            reasons.append(f"max_events={self._budget.max_events}")
        if self._llm_cost >= self._budget.max_llm_cost_usd:
            reasons.append(f"max_llm_cost_usd={self._budget.max_llm_cost_usd}")
        if elapsed >= self._budget.max_wall_seconds:
            reasons.append(f"max_wall_seconds={self._budget.max_wall_seconds} (elapsed={elapsed:.1f}s)")
        if depth >= self._budget.max_recursion_depth:
            reasons.append(f"max_recursion_depth={self._budget.max_recursion_depth} (depth={depth})")

        if reasons:
            yield KandoEvent(
                id=f"budget-{self._event_count}",
                type=BUDGET_EXHAUSTED,
                source=f"run:{self._run_id}",
                actor="budget-enforcer",
                cause=[event.id],
                timestamp=datetime.now(timezone.utc),
                data={"reasons": reasons, "event_count": self._event_count,
                      "llm_cost_usd": self._llm_cost, "elapsed_seconds": elapsed, "depth": depth},
            )
