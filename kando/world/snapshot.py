from __future__ import annotations
# Snapshot hydration and fallback (Phase 2).
# Placeholder — implementation forthcoming.

from kando.world.graph import World


def load_snapshot(run_id: str) -> tuple[World, int] | None:
    """Return (world, ledger_position) if a snapshot exists, else None."""
    raise NotImplementedError


def save_snapshot(run_id: str, world: World, position: int) -> None:
    raise NotImplementedError
