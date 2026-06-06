from __future__ import annotations
from kando.schema.events import KandoEvent


def build_lineage_index(events: list[KandoEvent]) -> dict[str, list[str]]:
    """Map each event ID to its causal ancestors (parent event IDs)."""
    return {e.id: e.cause for e in events}


def trace(event_id: str, index: dict[str, list[str]]) -> list[str]:
    """Return the full causal chain from event_id back to root, in order."""
    chain: list[str] = []
    seen: set[str] = set()
    queue = [event_id]
    while queue:
        eid = queue.pop(0)
        if eid in seen:
            continue
        seen.add(eid)
        chain.append(eid)
        queue.extend(index.get(eid, []))
    return chain
