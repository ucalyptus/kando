from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorldObject:
    id: str
    type: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Relation:
    id: str
    type: str        # e.g. "contradicts", "depends_on", "supports", "blocks"
    source_id: str
    target_id: str
    data: dict[str, Any] = field(default_factory=dict)


class World:
    """Live projected state — deterministically derived from the ledger."""

    def __init__(self) -> None:
        self.objects: dict[str, WorldObject] = {}
        self.relations: dict[str, Relation] = {}
        self.context: dict[str, Any] = {}   # runtime-level shared state (cache, config, etc.)

    def get_object(self, obj_id: str) -> WorldObject | None:
        return self.objects.get(obj_id)

    def get_relations(self, obj_id: str, relation_type: str | None = None) -> list[Relation]:
        rels = self._relations_for_object(obj_id)
        if relation_type:
            rels = [r for r in rels if r.type == relation_type]
        return rels

    def _relations_for_object(self, obj_id: str) -> list:
        """Return all relations that touch the given object."""
        return [
            r for r in self.relations.values()
            if r.source_id == obj_id or r.target_id == obj_id
        ]
