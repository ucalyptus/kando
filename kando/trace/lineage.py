from __future__ import annotations
from kando.schema.events import KandoEvent


def build_lineage_index(events: list[KandoEvent]) -> dict[str, list[str]]:
    """Map each event ID to its causal ancestors (parent event IDs)."""
    return {e.id: e.cause for e in events}


def trace(event_id: str, index: dict[str, list[str]]) -> list[str]:
    """Return the full causal chain from event_id back to root, in BFS order."""
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


def explain(event_id: str, events: list[KandoEvent]) -> list[KandoEvent]:
    """Return the full causal chain as actual event objects, in BFS order from event_id to root."""
    index = build_lineage_index(events)
    event_map: dict[str, KandoEvent] = {e.id: e for e in events}
    chain_ids = trace(event_id, index)
    return [event_map[eid] for eid in chain_ids if eid in event_map]
