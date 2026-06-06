"""Tests for the research kit: goal decomposition, findings, synthesis."""
from __future__ import annotations

from kando.ledger.memory import MemoryLedgerStore
from kando.runtime import Runtime

from kits.research.kit import (
    GOAL, QUESTION, FINDING, SYNTHESIS,
    DECOMPOSES_INTO, ANSWERS, SYNTHESIZES,
    create_kit, seed_from_goal,
)


def _run(seed_events):
    store = MemoryLedgerStore("research-test")
    world = Runtime(ledger=store, responders=create_kit()).run(seed_events)
    return world, list(store.read_all())


def test_seed_from_goal_creates_goal_event():
    events = seed_from_goal("Understand AI safety", "abc000")
    assert len(events) == 1
    e = events[0]
    assert e.data["type"] == GOAL
    assert "AI safety" in e.data["data"]["text"]


def test_goal_decomposes_into_questions():
    seed = seed_from_goal("Evaluate climate tech", "run001")
    world, _ = _run(seed)
    obj_types = {o.type for o in world.objects.values()}
    assert GOAL in obj_types
    assert QUESTION in obj_types
    questions = [o for o in world.objects.values() if o.type == QUESTION]
    assert len(questions) >= 3  # default decomposition: 3 angles


def test_decomposes_into_relations_created():
    seed = seed_from_goal("Blockchain adoption", "run002")
    world, _ = _run(seed)
    rel_types = {r.type for r in world.relations.values()}
    assert DECOMPOSES_INTO in rel_types


def test_questions_produce_findings():
    seed = seed_from_goal("Quantum computing", "run003")
    world, _ = _run(seed)
    findings = [o for o in world.objects.values() if o.type == FINDING]
    questions = [o for o in world.objects.values() if o.type == QUESTION]
    assert len(findings) >= len(questions)


def test_answers_relations_created():
    seed = seed_from_goal("Edge computing", "run004")
    world, _ = _run(seed)
    rel_types = {r.type for r in world.relations.values()}
    assert ANSWERS in rel_types


def test_synthesis_created_when_all_questions_have_findings():
    seed = seed_from_goal("Renewable energy", "run005")
    world, _ = _run(seed)
    # With 3 questions each auto-answered, synthesis should fire
    syntheses = [o for o in world.objects.values() if o.type == SYNTHESIS]
    assert len(syntheses) == 1


def test_synthesizes_relation_links_to_goal():
    seed = seed_from_goal("5G networks", "run006")
    world, _ = _run(seed)
    rel_types = {r.type for r in world.relations.values()}
    assert SYNTHESIZES in rel_types
    goal_obj = next(o for o in world.objects.values() if o.type == GOAL)
    synth_rels = [
        r for r in world.relations.values()
        if r.type == SYNTHESIZES and r.target_id == goal_obj.id
    ]
    assert len(synth_rels) == 1


def test_create_kit_returns_three_responders():
    responders = create_kit()
    assert len(responders) == 3
    names = {r.name for r in responders}
    assert "research.on_goal_created" in names
    assert "research.on_question_created" in names
    assert "research.on_finding_created" in names
