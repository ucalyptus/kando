from __future__ import annotations
from typing import Iterator
from kando.schema.events import KandoEvent
from kando.branch.fork import BranchMeta


def read_branch(meta: BranchMeta, parent_store, branch_store) -> Iterator[KandoEvent]:
    """Yield events: shared prefix from parent, divergent tail from branch."""
    yield from parent_store.read(from_position=0)   # events 0..fork_position
    yield from branch_store.read(from_position=0)   # events after fork point
