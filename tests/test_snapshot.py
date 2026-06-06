"""Tests for World snapshot save/load roundtrip."""
from __future__ import annotations

import json
import os
import pytest
from pathlib import Path

from kando.world.graph import World, WorldObject, Relation
from kando.world.snapshot import save_snapshot, load_snapshot


@pytest.fixture(autouse=True)
def tmp_snapshot_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("KANDO_SNAPSHOT_DIR", str(tmp_path / "snapshots"))
    # Force module to re-read env var
    import kando.world.snapshot as snap
    snap._SNAPSHOT_DIR = Path(str(tmp_path / "snapshots"))
    yield
    snap._SNAPSHOT_DIR = Path(os.environ.get("KANDO_SNAPSHOT_DIR", ".kando_snapshots"))


def _world_with_objects() -> World:
    w = World()
    w.objects["obj-a"] = WorldObject(id="obj-a", type="claim", data={"text": "hello"})
    w.objects["obj-b"] = WorldObject(id="obj-b", type="claim", data={"text": "world", "score": 42})
    w.relations["rel-1"] = Relation(
        id="rel-1", type="supports",
        source_id="obj-a", target_id="obj-b", data={}
    )
    return w


def test_load_snapshot_returns_none_when_missing():
    assert load_snapshot("nonexistent-run") is None


def test_save_and_load_roundtrip():
    w = _world_with_objects()
    save_snapshot("run-abc", w, position=7)
    result = load_snapshot("run-abc")
    assert result is not None
    restored_world, position = result
    assert position == 7
    assert set(restored_world.objects.keys()) == {"obj-a", "obj-b"}
    assert restored_world.objects["obj-a"].type == "claim"
    assert restored_world.objects["obj-b"].data["score"] == 42


def test_snapshot_preserves_relations():
    w = _world_with_objects()
    save_snapshot("run-rel", w, position=3)
    restored_world, _ = load_snapshot("run-rel")
    assert "rel-1" in restored_world.relations
    rel = restored_world.relations["rel-1"]
    assert rel.type == "supports"
    assert rel.source_id == "obj-a"
    assert rel.target_id == "obj-b"


def test_snapshot_empty_world():
    w = World()
    save_snapshot("run-empty", w, position=0)
    result = load_snapshot("run-empty")
    assert result is not None
    restored_world, position = result
    assert position == 0
    assert restored_world.objects == {}
    assert restored_world.relations == {}


def test_snapshot_creates_directory():
    import kando.world.snapshot as snap
    assert not snap._SNAPSHOT_DIR.exists()
    save_snapshot("run-mkdir", World(), position=0)
    assert snap._SNAPSHOT_DIR.exists()


def test_snapshot_overwrites_previous():
    w1 = World()
    w1.objects["obj-x"] = WorldObject(id="obj-x", type="t", data={"v": 1})
    save_snapshot("run-overwrite", w1, position=1)

    w2 = World()
    w2.objects["obj-y"] = WorldObject(id="obj-y", type="t", data={"v": 2})
    save_snapshot("run-overwrite", w2, position=5)

    restored_world, position = load_snapshot("run-overwrite")
    assert position == 5
    assert "obj-y" in restored_world.objects
    assert "obj-x" not in restored_world.objects


def test_snapshot_file_is_valid_json(tmp_path):
    import kando.world.snapshot as snap
    w = _world_with_objects()
    save_snapshot("run-json", w, position=4)
    path = snap._SNAPSHOT_DIR / "run-json.json"
    payload = json.loads(path.read_text())
    assert "world" in payload
    assert "position" in payload
    assert payload["position"] == 4
    assert isinstance(payload["world"]["objects"], list)
    assert isinstance(payload["world"]["relations"], list)
