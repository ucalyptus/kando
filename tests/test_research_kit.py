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


def test_create_kit_returns_five_responders():
    responders = create_kit()
    assert len(responders) == 5
    names = {r.name for r in responders}
    assert "research.on_goal_created" in names
    assert "research.on_question_created" in names
    assert "research.on_finding_created" in names
    assert "research.on_pending_finding_created" in names
    assert "research.on_llm_response" in names


def test_pending_finding_emits_llm_request():
    """Each question should produce an LLM_REQUEST when no executor is wired."""
    from kando.schema.events import LLM_REQUEST
    seed = seed_from_goal("Fusion energy", "run007")
    store = MemoryLedgerStore("research-llm-req")
    Runtime(ledger=store, responders=create_kit()).run(seed)
    all_events = list(store.read_all())
    llm_reqs = [e for e in all_events if e.type == LLM_REQUEST]
    assert len(llm_reqs) == 3  # one per question


def test_executor_patches_findings_to_complete():
    """With a fake executor wired in, findings should be patched to status=complete."""
    from kando.schema.events import OBJECT_PATCHED
    from kando.responders.llm_executor import LLMExecutorResponder

    def fake_llm(messages, model, max_tokens):
        return "Fake answer: " + messages[0]["content"][:30], 0.001

    seed = seed_from_goal("Space tourism", "run008")
    store = MemoryLedgerStore("research-executor")
    responders = create_kit() + [LLMExecutorResponder(fake_llm)]
    world = Runtime(ledger=store, responders=responders).run(seed)

    findings = [o for o in world.objects.values() if o.type == FINDING]
    assert all(f.data.get("status") == "complete" for f in findings)
    assert all(f.data.get("text", "").startswith("Fake answer") for f in findings)
