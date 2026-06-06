"""Tests for the expanded diligence kit: Contradiction, Report, and all edge types."""
from __future__ import annotations

from datetime import datetime, timezone

from kando.ledger.memory import MemoryLedgerStore
from kando.runtime import Runtime
from kando.schema.events import KandoEvent, OBJECT_CREATED

from kits.diligence.kit import (
    COMPANY, CLAIM, EVIDENCE, CONTRADICTION, REPORT,
    SUPPORTS, CONTRADICTS, DEPENDS_ON, SOURCED_FROM,
    create_kit, seed_from_goal,
)


def _ts():
    return datetime.now(timezone.utc)


def _run(seed_events):
    store = MemoryLedgerStore("diligence-test")
    world = Runtime(ledger=store, responders=create_kit()).run(seed_events)
    return world, list(store.read_all())


def test_seed_from_goal_creates_company_event():
    events = seed_from_goal("Stripe", "abc123def456")
    assert len(events) == 1
    e = events[0]
    assert e.data["type"] == COMPANY
    assert e.data["data"]["name"] == "Stripe"


def test_company_triggers_pending_claim():
    seed = seed_from_goal("Acme", "runid000")
    world, all_events = _run(seed)
    obj_types = {o.type for o in world.objects.values()}
    assert COMPANY in obj_types
    assert CLAIM in obj_types


def test_evidence_creates_sourced_from_relation():
    store = MemoryLedgerStore("dil-evidence")
    # First run just company → claim
    seed = seed_from_goal("TestCo", "run00001")
    world = Runtime(ledger=store, responders=create_kit()).run(seed)
    claim_obj = next(o for o in world.objects.values() if o.type == CLAIM)

    # Now append an Evidence event for the claim
    ev_id = "evidence-001"
    ev_event = KandoEvent(
        ev_id, OBJECT_CREATED, "run:run00001", "test", [claim_obj.id], _ts(),
        {"id": ev_id, "type": EVIDENCE, "data": {"text": "Proof", "claim_id": claim_obj.id}},
    )
    world2 = Runtime(ledger=store, responders=create_kit()).run([ev_event])
    all_events = list(store.read_all())

    rel_types = {r.type for r in world2.relations.values()}
    assert SOURCED_FROM in rel_types


def test_contradiction_creates_contradicts_relation():
    store = MemoryLedgerStore("dil-contradiction")
    seed = seed_from_goal("TargetCo", "run00002")
    world = Runtime(ledger=store, responders=create_kit()).run(seed)

    # Add a second Claim so we have two to contradict
    c2_id = "claim-extra-001"
    c2_event = KandoEvent(
        c2_id, OBJECT_CREATED, "run:run00002", "test", [], _ts(),
        {"id": c2_id, "type": CLAIM, "data": {"text": "Another claim", "company_id": "company-run00002"}},
    )
    world = Runtime(ledger=store, responders=create_kit()).run([c2_event])
    claim_ids = [o.id for o in world.objects.values() if o.type == CLAIM]
    assert len(claim_ids) >= 2

    # Create a Contradiction between two claims
    contr_id = "contradiction-001"
    contr_event = KandoEvent(
        contr_id, OBJECT_CREATED, "run:run00002", "test", [], _ts(),
        {
            "id": contr_id,
            "type": CONTRADICTION,
            "data": {
                "claim_a_id": claim_ids[0],
                "claim_b_id": claim_ids[1],
                "reason": "They disagree",
            },
        },
    )
    world = Runtime(ledger=store, responders=create_kit()).run([contr_event])
    rel_types = {r.type for r in world.relations.values()}
    assert CONTRADICTS in rel_types


def test_pending_claim_emits_llm_request():
    from kando.schema.events import LLM_REQUEST
    seed = seed_from_goal("Nvidia", "run00010")
    store = MemoryLedgerStore("dil-llm-req")
    Runtime(ledger=store, responders=create_kit()).run(seed)
    all_events = list(store.read_all())
    llm_reqs = [e for e in all_events if e.type == LLM_REQUEST]
    assert len(llm_reqs) == 1
    assert "Nvidia" in llm_reqs[0].data["messages"][0]["content"]


def test_executor_patches_claim_to_complete():
    from kando.responders.llm_executor import LLMExecutorResponder

    def fake_llm(messages, model, max_tokens):
        return "Fake diligence: " + messages[0]["content"][:20], 0.001

    seed = seed_from_goal("Tesla", "run00011")
    store = MemoryLedgerStore("dil-executor")
    responders = create_kit() + [LLMExecutorResponder(fake_llm)]
    world = Runtime(ledger=store, responders=responders).run(seed)

    claims = [o for o in world.objects.values() if o.type == CLAIM]
    assert len(claims) == 1
    assert claims[0].data.get("status") == "complete"
    assert claims[0].data.get("text", "").startswith("Fake diligence")


def test_report_creates_depends_on_relation():
    store = MemoryLedgerStore("dil-report")
    seed = seed_from_goal("ReportCo", "run00003")
    world = Runtime(ledger=store, responders=create_kit()).run(seed)
    company_obj = next(o for o in world.objects.values() if o.type == COMPANY)

    rpt_id = "report-001"
    rpt_event = KandoEvent(
        rpt_id, OBJECT_CREATED, "run:run00003", "test", [], _ts(),
        {"id": rpt_id, "type": REPORT,
         "data": {"summary": "All clear", "company_id": company_obj.id}},
    )
    world = Runtime(ledger=store, responders=create_kit()).run([rpt_event])
    rel_types = {r.type for r in world.relations.values()}
    assert DEPENDS_ON in rel_types
