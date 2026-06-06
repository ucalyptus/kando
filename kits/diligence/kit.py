"""Diligence kit: structured due-diligence on a company or entity."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator

from kando.responders.base import Responder
from kando.schema.events import (
    KandoEvent, OBJECT_CREATED, OBJECT_PATCHED, RELATION_CREATED,
    LLM_REQUEST, LLM_RESPONSE, make_event,
)
from kando.world.graph import World


# ---------------------------------------------------------------------------
# Object type tags
# ---------------------------------------------------------------------------

COMPANY      = "Company"
CLAIM        = "Claim"
EVIDENCE     = "Evidence"
CONTRADICTION = "Contradiction"
REPORT       = "Report"

# ---------------------------------------------------------------------------
# Relation type tags
# ---------------------------------------------------------------------------

SUPPORTS     = "supports"
CONTRADICTS  = "contradicts"
DEPENDS_ON   = "depends_on"
SOURCED_FROM = "sourced_from"


# ---------------------------------------------------------------------------
# Domain dataclasses (typed view over WorldObject.data)
# ---------------------------------------------------------------------------

@dataclass
class Company:
    id: str
    name: str


@dataclass
class Claim:
    id: str
    text: str
    company_id: str


@dataclass
class Evidence:
    id: str
    text: str
    claim_id: str


@dataclass
class Contradiction:
    id: str
    claim_a_id: str
    claim_b_id: str
    reason: str


@dataclass
class Report:
    id: str
    company_id: str
    summary: str


# ---------------------------------------------------------------------------
# Responders
# ---------------------------------------------------------------------------

def _on_company_created(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
    """When a Company is created, emit an initial pending-research Claim."""
    if event.data.get("type") != COMPANY:
        return

    company_id = event.data["id"]
    company_name = event.data.get("data", {}).get("name", company_id)
    claim_id = f"claim-{uuid.uuid4().hex[:8]}"

    yield make_event(
        type=OBJECT_CREATED,
        source=event.source,
        actor="diligence.on_company_created",
        cause=[event.id],
        data={
            "id": claim_id,
            "type": CLAIM,
            "data": {
                "text": f"Pending research for {company_name}",
                "company_id": company_id,
                "status": "pending",
            },
        },
    )


def _on_evidence_created(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
    """When Evidence is created, link it to its parent Claim via sourced_from."""
    if event.data.get("type") != EVIDENCE:
        return

    evidence_id = event.data["id"]
    claim_id = event.data.get("data", {}).get("claim_id")
    if not claim_id or claim_id not in world.objects:
        return

    yield make_event(
        type=RELATION_CREATED,
        source=event.source,
        actor="diligence.on_evidence_created",
        cause=[event.id],
        data={
            "id": f"rel-sourced-{uuid.uuid4().hex[:8]}",
            "type": SOURCED_FROM,
            "source_id": evidence_id,
            "target_id": claim_id,
        },
    )


def _on_claim_with_evidence(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
    """When a Claim is created, link any existing Evidence for it via supports."""
    if event.data.get("type") != CLAIM:
        return

    claim_id = event.data["id"]
    for obj in world.objects.values():
        if obj.type == EVIDENCE and obj.data.get("claim_id") == claim_id:
            yield make_event(
                type=RELATION_CREATED,
                source=event.source,
                actor="diligence.claim_evidence_linker",
                cause=[event.id],
                data={
                    "id": f"rel-supports-{uuid.uuid4().hex[:8]}",
                    "type": SUPPORTS,
                    "source_id": obj.id,
                    "target_id": claim_id,
                },
            )


def _on_contradiction_created(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
    """When a Contradiction is created, emit a contradicts relation between the two claims."""
    if event.data.get("type") != CONTRADICTION:
        return

    obj_data = event.data.get("data", {})
    claim_a = obj_data.get("claim_a_id")
    claim_b = obj_data.get("claim_b_id")
    if claim_a and claim_b and claim_a in world.objects and claim_b in world.objects:
        yield make_event(
            type=RELATION_CREATED,
            source=event.source,
            actor="diligence.on_contradiction_created",
            cause=[event.id],
            data={
                "id": f"rel-contradicts-{uuid.uuid4().hex[:8]}",
                "type": CONTRADICTS,
                "source_id": claim_a,
                "target_id": claim_b,
            },
        )


def _on_report_requested(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
    """When a Report is created, link it to its Company via depends_on."""
    if event.data.get("type") != REPORT:
        return

    report_id = event.data["id"]
    company_id = event.data.get("data", {}).get("company_id")
    if not company_id or company_id not in world.objects:
        return

    yield make_event(
        type=RELATION_CREATED,
        source=event.source,
        actor="diligence.on_report_requested",
        cause=[event.id],
        data={
            "id": f"rel-depends-{uuid.uuid4().hex[:8]}",
            "type": DEPENDS_ON,
            "source_id": report_id,
            "target_id": company_id,
        },
    )


def _on_pending_claim_created(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
    """When a pending-research Claim is created, emit an LLM_REQUEST to fill it in."""
    if event.data.get("type") != CLAIM:
        return
    if event.data.get("data", {}).get("status") != "pending":
        return

    claim_id = event.data["id"]
    company_id = event.data.get("data", {}).get("company_id", "")
    company_name = (
        world.objects[company_id].data.get("name", company_id)
        if company_id in world.objects
        else company_id
    )

    yield make_event(
        type=LLM_REQUEST,
        source=event.source,
        actor="diligence.on_pending_claim_created",
        cause=[event.id],
        data={
            "messages": [{
                "role": "user",
                "content": (
                    f"Provide a brief due diligence summary for {company_name}. "
                    "Cover: key facts, business model, risks, and recent developments."
                ),
            }],
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 1024,
            "cause_object_id": claim_id,
        },
    )


def _on_llm_response(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
    """When an LLM response arrives for a Claim, patch it with real content."""
    claim_id = event.data.get("cause_object_id", "")
    if not claim_id or claim_id not in world.objects:
        return
    if world.objects[claim_id].type != CLAIM:
        return

    yield make_event(
        type=OBJECT_PATCHED,
        source=event.source,
        actor="diligence.on_llm_response",
        cause=[event.id],
        data={
            "id": claim_id,
            "patch": {"text": event.data.get("text", ""), "status": "complete"},
        },
    )


# ---------------------------------------------------------------------------
# Kit factory
# ---------------------------------------------------------------------------

def seed_from_goal(goal: str, run_id: str) -> list[KandoEvent]:
    """Turn a free-text goal into seed events for a diligence run."""
    company_id = f"company-{run_id[:8]}"
    return [
        KandoEvent(
            id=f"company.created-{run_id[:8]}",
            type=OBJECT_CREATED,
            source=f"run:{run_id}",
            actor="cli",
            cause=[],
            timestamp=datetime.now(timezone.utc),
            data={"id": company_id, "type": COMPANY, "data": {"name": goal}},
        )
    ]


def create_kit() -> list[Responder]:
    """Return all responders that compose the diligence kit."""
    return [
        Responder(
            name="diligence.on_company_created",
            pattern=frozenset({OBJECT_CREATED}),
            fn=_on_company_created,
        ),
        Responder(
            name="diligence.on_evidence_created",
            pattern=frozenset({OBJECT_CREATED}),
            fn=_on_evidence_created,
        ),
        Responder(
            name="diligence.claim_evidence_linker",
            pattern=frozenset({OBJECT_CREATED}),
            fn=_on_claim_with_evidence,
        ),
        Responder(
            name="diligence.on_contradiction_created",
            pattern=frozenset({OBJECT_CREATED}),
            fn=_on_contradiction_created,
        ),
        Responder(
            name="diligence.on_report_requested",
            pattern=frozenset({OBJECT_CREATED}),
            fn=_on_report_requested,
        ),
        Responder(
            name="diligence.on_pending_claim_created",
            pattern=frozenset({OBJECT_CREATED}),
            fn=_on_pending_claim_created,
        ),
        Responder(
            name="diligence.on_llm_response",
            pattern=frozenset({LLM_RESPONSE}),
            fn=_on_llm_response,
        ),
    ]
