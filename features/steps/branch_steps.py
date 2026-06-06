from __future__ import annotations
from pytest_bdd import scenarios, given, when, then, parsers
from kando.branch.fork import fork, BranchMeta
from kando.branch.diff import diff, WorldDiff
from kando.world.graph import World, WorldObject, Relation

scenarios('../branch.feature')


@given(parsers.parse('a run "{run_id}" with {n:d} events'), target_fixture='branch_ctx')
def run_with_events(run_id, n):
    return {"run_id": run_id, "n_events": n, "meta": None, "diff": None,
            "world_a": None, "world_b": None}


@given(parsers.parse('world A with no objects'), target_fixture='branch_ctx')
def world_a_empty():
    return {
        "world_a": World(),
        "world_b": None,
        "meta": None,
        "diff": None,
        "summary_diff": None,
    }


@given(parsers.parse('world B with object "{obj_id}"'))
def world_b_with_object(branch_ctx, obj_id):
    world_b = World()
    world_b.objects[obj_id] = WorldObject(id=obj_id, type="thing", data={})
    branch_ctx["world_b"] = world_b


@given('two identical worlds with the same objects and relations', target_fixture='branch_ctx')
def two_identical_worlds():
    w1 = World()
    w1.objects["x"] = WorldObject(id="x", type="claim", data={"v": 1})
    w2 = World()
    w2.objects["x"] = WorldObject(id="x", type="claim", data={"v": 1})
    return {"world_a": w1, "world_b": w2, "meta": None, "diff": None, "summary_diff": None}


@given('a diff with 2 added objects and 1 removed relation', target_fixture='branch_ctx')
def diff_with_changes():
    d = WorldDiff(
        added_objects=["a", "b"],
        removed_objects=[],
        patched_objects=[],
        added_relations=[],
        removed_relations=["r1"],
    )
    return {"diff": d, "world_a": None, "world_b": None, "meta": None, "summary_diff": None}


@when(parsers.parse('I fork at position {pos:d} creating "{branch_id}"'))
def do_fork(branch_ctx, pos, branch_id):
    meta = fork(
        parent_run_id=branch_ctx["run_id"],
        fork_position=pos,
        branch_id=branch_id,
    )
    branch_ctx["meta"] = meta


@when('I diff them')
def do_diff(branch_ctx):
    branch_ctx["diff"] = diff(branch_ctx["world_a"], branch_ctx["world_b"])


@when('I diff A against B')
def do_diff_ab(branch_ctx):
    branch_ctx["diff"] = diff(branch_ctx["world_a"], branch_ctx["world_b"])


@when('I call summary')
def do_summary(branch_ctx):
    branch_ctx["summary_result"] = branch_ctx["diff"].summary()


@then(parsers.parse('branch metadata has parent_run_id "{expected}"'))
def check_parent_run_id(branch_ctx, expected):
    assert branch_ctx["meta"].parent_run_id == expected, (
        f"Expected parent_run_id={expected}, got {branch_ctx['meta'].parent_run_id}"
    )


@then(parsers.parse('branch metadata has fork_position {pos:d}'))
def check_fork_position(branch_ctx, pos):
    assert branch_ctx["meta"].fork_position == pos, (
        f"Expected fork_position={pos}, got {branch_ctx['meta'].fork_position}"
    )


@then('the diff is empty')
def check_diff_empty(branch_ctx):
    d = branch_ctx["diff"]
    assert not bool(d), f"Expected empty diff but got: {d}"


@then(parsers.parse('added_objects contains "{obj_id}"'))
def check_added_objects(branch_ctx, obj_id):
    assert obj_id in branch_ctx["diff"].added_objects, (
        f"{obj_id} not in added_objects: {branch_ctx['diff'].added_objects}"
    )


@then(parsers.parse('the result is "{expected}"'))
def check_summary_result(branch_ctx, expected):
    result = branch_ctx["summary_result"]
    assert result == expected, f"Expected '{expected}', got '{result}'"
