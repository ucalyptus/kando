from __future__ import annotations
from dataclasses import dataclass


@dataclass
class BranchMeta:
    branch_id: str
    parent_run_id: str
    fork_position: int      # events 0..fork_position are shared from parent


def fork(parent_run_id: str, fork_position: int, branch_id: str) -> BranchMeta:
    return BranchMeta(
        branch_id=branch_id,
        parent_run_id=parent_run_id,
        fork_position=fork_position,
    )
