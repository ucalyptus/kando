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
