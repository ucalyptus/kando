"""Snapshot: serialise/deserialise a World checkpoint to disk."""
from __future__ import annotations

import json
import os
from pathlib import Path

from kando.world.graph import World, WorldObject, Relation

_SNAPSHOT_DIR = Path(os.environ.get("KANDO_SNAPSHOT_DIR", ".kando_snapshots"))


def _snapshot_path(run_id: str) -> Path:
    return _SNAPSHOT_DIR / f"{run_id}.json"


def _world_to_dict(world: World) -> dict:
    return {
        "objects": [
            {"id": o.id, "type": o.type, "data": o.data}
            for o in world.objects.values()
        ],
        "relations": [
            {"id": r.id, "type": r.type, "source_id": r.source_id,
             "target_id": r.target_id, "data": r.data}
            for r in world.relations.values()
        ],
    }


def _world_from_dict(d: dict) -> World:
    world = World()
    for obj in d["objects"]:
        world.objects[obj["id"]] = WorldObject(
            id=obj["id"], type=obj["type"], data=obj.get("data", {})
        )
    for rel in d.get("relations", []):
        world.relations[rel["id"]] = Relation(
            id=rel["id"], type=rel["type"],
            source_id=rel["source_id"], target_id=rel["target_id"],
            data=rel.get("data", {}),
        )
    return world


def load_snapshot(run_id: str) -> tuple[World, int] | None:
    """Return (world, ledger_position) if a snapshot exists, else None."""
    path = _snapshot_path(run_id)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
        return _world_from_dict(payload["world"]), payload["position"]
    except Exception:
        return None


def save_snapshot(run_id: str, world: World, position: int) -> None:
    """Persist a world checkpoint to disk."""
    _SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    _snapshot_path(run_id).write_text(
        json.dumps({"world": _world_to_dict(world), "position": position}, indent=2)
    )
