"""Property-based tests using Hypothesis for core Kando contracts."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import List

from hypothesis import given, settings, assume
from hypothesis import strategies as st
from hypothesis.strategies import composite

from kando.cache.llm import LLMCache, ScopedLLMCache
from kando.ledger.memory import MemoryLedgerStore
from kando.branch.diff import WorldDiff, diff
from kando.schema.events import KandoEvent, OBJECT_CREATED
from kando.world.graph import World, WorldObject
from kando.world.projection import project


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts():
    return datetime.now(timezone.utc)


def _make_created(obj_id: str) -> KandoEvent:
    return KandoEvent(
        id=f"create-{obj_id}",
        type=OBJECT_CREATED,
        source="run:prop-test",
        actor="prop-test",
        cause=[],
        timestamp=_ts(),
        data={"id": obj_id, "type": "claim", "data": {}},
    )


# Strategy: unique object ID lists (short ASCII strings)
_obj_ids = st.lists(
    st.text(alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), min_codepoint=65), min_size=1, max_size=8),
    min_size=0,
    max_size=20,
    unique=True,
)

# Strategy: JSON-serializable dict (string keys, simple values)
_simple_dict = st.dictionaries(
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=6),
    st.one_of(st.integers(), st.text(min_size=0, max_size=10), st.booleans()),
    max_size=5,
)


# ---------------------------------------------------------------------------
# Property 1: project(events) world has exactly as many objects as
#             OBJECT_CREATED events (assuming distinct IDs)
# ---------------------------------------------------------------------------
@given(_obj_ids)
def test_projection_object_count(obj_ids):
    """World object count equals number of distinct OBJECT_CREATED events."""
    events = [_make_created(oid) for oid in obj_ids]
    world = project(events)
    assert len(world.objects) == len(obj_ids)


# ---------------------------------------------------------------------------
# Property 2: append(events) always returns len(events) added to current pos
# ---------------------------------------------------------------------------
@given(
    st.lists(st.integers(min_value=0, max_value=100), min_size=0, max_size=30),
    st.lists(st.integers(min_value=0, max_value=100), min_size=0, max_size=30),
)
def test_append_position_accumulates(batch1_sizes, batch2_sizes):
    """Each append returns total event count so far."""
    store = MemoryLedgerStore("prop-append")
    running_total = 0

    for size in batch1_sizes + batch2_sizes:
        events = [_make_created(f"obj-{running_total + i}") for i in range(size)]
        pos = store.append(events)
        running_total += size
        assert pos == running_total, f"Expected {running_total}, got {pos}"


# ---------------------------------------------------------------------------
# Property 3: LLMCache put-then-get is identity for any serializable request
# ---------------------------------------------------------------------------
@given(_simple_dict, st.text(min_size=0, max_size=50))
def test_llm_cache_put_get_identity(request_dict, response):
    """Putting then getting returns exactly the stored response."""
    cache = LLMCache()
    cache.put(request_dict, response)
    result = cache.get(request_dict)
    assert result == response, f"Expected '{response}', got '{result}'"


# ---------------------------------------------------------------------------
# Property 4: WorldDiff(a, a) is always empty (reflexivity)
# ---------------------------------------------------------------------------
@given(_obj_ids)
def test_world_diff_reflexivity(obj_ids):
    """Diffing a world against itself is always empty."""
    world = World()
    for oid in obj_ids:
        world.objects[oid] = WorldObject(id=oid, type="claim", data={})
    d = diff(world, world)
    assert not bool(d), f"Diff of world with itself should be empty, got: {d}"
    assert d.added_objects == []
    assert d.removed_objects == []
    assert d.patched_objects == []
    assert d.added_relations == []
    assert d.removed_relations == []


# ---------------------------------------------------------------------------
# Property 5: ScopedLLMCache.get falls back to parent for any request not
#             in local store
# ---------------------------------------------------------------------------
@given(_simple_dict, st.text(min_size=1, max_size=20), st.text(min_size=0, max_size=50))
def test_scoped_cache_fallback_to_parent(request_dict, prefix, response):
    """Scoped cache falls back to parent on local miss."""
    parent = LLMCache()
    parent.put(request_dict, response)
    scoped = parent.scope(prefix)
    # Nothing stored locally in scoped cache — should fall back to parent
    result = scoped.get(request_dict)
    assert result == response, f"Expected parent response '{response}', got '{result}'"


# ---------------------------------------------------------------------------
# Property 6: Projection is order-independent for OBJECT_CREATED-only streams
#             with distinct IDs (all events are independent)
# ---------------------------------------------------------------------------
@given(_obj_ids)
def test_projection_order_independence(obj_ids):
    """If all events create distinct objects, any permutation gives the same world."""
    assume(len(obj_ids) > 0)
    events = [_make_created(oid) for oid in obj_ids]
    world_forward = project(events)
    world_reversed = project(list(reversed(events)))
    assert set(world_forward.objects.keys()) == set(world_reversed.objects.keys()), (
        "Projection should contain same objects regardless of order"
    )


# ---------------------------------------------------------------------------
# Property 7: project(events)[obj_id].data matches what was put in
# ---------------------------------------------------------------------------
@given(
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=8),
    _simple_dict,
)
def test_projection_preserves_data(obj_id, data):
    """Object data in projected world matches the event data."""
    event = KandoEvent(
        id=f"create-{obj_id}",
        type=OBJECT_CREATED,
        source="run:prop-test",
        actor="test",
        cause=[],
        timestamp=_ts(),
        data={"id": obj_id, "type": "claim", "data": data},
    )
    world = project([event])
    assert obj_id in world.objects
    assert world.objects[obj_id].data == data
