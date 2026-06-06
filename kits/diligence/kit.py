"""Diligence kit: object types, responders, and kit factory."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterator

from kando.responders.base import Responder
from kando.schema.events import KandoEvent, OBJECT_CREATED, make_event
from kando.world.graph import World


# ---------------------------------------------------------------------------
# Domain object type tags
# ---------------------------------------------------------------------------

COMPANY  = "Company"
CLAIM    = "Claim"
EVIDENCE = "Evidence"


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


# ---------------------------------------------------------------------------
# Responder implementations
# ---------------------------------------------------------------------------

_COUNTER = 0


def _next_id(prefix: str) -> str:
    global _COUNTER
    _COUNTER += 1
    return f"{prefix}-{_COUNTER}"


def _on_company_created(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
    """When a Company object is created, emit a pending-research Claim."""
    obj_data = event.data.get("data", {})
    obj_type = event.data.get("type", "")
    if obj_type != COMPANY:
        return

    company_id = event.data["id"]
    company_name = obj_data.get("name", company_id)
    claim_id = _next_id("claim")

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
            },
        },
        run_id_counter=_COUNTER,
    )


# ---------------------------------------------------------------------------
# Kit factory
# ---------------------------------------------------------------------------

def seed_from_goal(goal: str, run_id: str) -> list[KandoEvent]:
    """Turn a free-text goal into seed events for a diligence run.

    Treats the goal string as the company name to investigate.
    """
    from datetime import datetime, timezone
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
    """Return the list of responders that make up the diligence kit."""
    return [
        Responder(
            name="diligence.on_company_created",
            pattern=frozenset({OBJECT_CREATED}),
            fn=_on_company_created,
        ),
    ]
