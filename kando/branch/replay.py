from __future__ import annotations
from typing import Iterator
from kando.schema.events import KandoEvent
from kando.branch.fork import BranchMeta


def read_branch(meta: BranchMeta, parent_store, branch_store) -> Iterator[KandoEvent]:
    """Yield events: shared prefix (0..fork_position) from parent, then branch tail."""
    prefix = list(parent_store.read(from_position=0))[: meta.fork_position]
    yield from prefix
    yield from branch_store.read(from_position=0)
