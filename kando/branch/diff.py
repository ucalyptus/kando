from __future__ import annotations
from dataclasses import dataclass
from kando.world.graph import World


@dataclass
class WorldDiff:
    added_objects: list[str]
    removed_objects: list[str]
    patched_objects: list[str]
    added_relations: list[str]
    removed_relations: list[str]

    def __bool__(self) -> bool:
        """True if any field is non-empty (i.e. there are actual differences)."""
        return bool(
            self.added_objects
            or self.removed_objects
            or self.patched_objects
            or self.added_relations
            or self.removed_relations
        )

    def summary(self) -> str:
        """Human-readable one-line summary of the diff."""
        parts = self._object_parts() + self._relation_parts()
        return ", ".join(parts) if parts else "no changes"

    def _object_parts(self) -> list:
        """Build the objects portion of the summary."""
        parts = []
        if self.added_objects:
            parts.append(f"+{len(self.added_objects)} objects")
        if self.removed_objects:
            parts.append(f"-{len(self.removed_objects)} objects")
        if self.patched_objects:
            parts.append(f"~{len(self.patched_objects)} objects patched")
        return parts

    def _relation_parts(self) -> list:
        """Build the relations portion of the summary."""
        parts = []
        if self.added_relations:
            parts.append(f"+{len(self.added_relations)} relations")
        if self.removed_relations:
            parts.append(f"-{len(self.removed_relations)} relations")
        return parts


def diff(world_a: World, world_b: World) -> WorldDiff:
    a_objs = set(world_a.objects)
    b_objs = set(world_b.objects)
    a_rels = set(world_a.relations)
    b_rels = set(world_b.relations)

    patched = [
        oid for oid in a_objs & b_objs
        if world_a.objects[oid].data != world_b.objects[oid].data
    ]

    return WorldDiff(
        added_objects=sorted(b_objs - a_objs),
        removed_objects=sorted(a_objs - b_objs),
        patched_objects=patched,
        added_relations=sorted(b_rels - a_rels),
        removed_relations=sorted(a_rels - b_rels),
    )
