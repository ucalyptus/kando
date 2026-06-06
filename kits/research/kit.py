"""Research kit: decompose a goal into sub-questions, gather sources, synthesize findings."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator

from kando.responders.base import Responder
from kando.schema.events import KandoEvent, OBJECT_CREATED, RELATION_CREATED, make_event
from kando.world.graph import World


# ---------------------------------------------------------------------------
# Object type tags
# ---------------------------------------------------------------------------

GOAL         = "Goal"
QUESTION     = "Question"
SOURCE       = "Source"
FINDING      = "Finding"
SYNTHESIS    = "Synthesis"

# ---------------------------------------------------------------------------
# Relation type tags
# ---------------------------------------------------------------------------

DECOMPOSES_INTO = "decomposes_into"  # Goal -> Question
ANSWERS         = "answers"          # Finding -> Question
SYNTHESIZES     = "synthesizes"      # Synthesis -> Finding
CITES           = "cites"            # Finding -> Source


# ---------------------------------------------------------------------------
# Domain dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Goal:
    id: str
    text: str


@dataclass
class Question:
    id: str
    text: str
    goal_id: str


@dataclass
class Source:
    id: str
    url: str
    question_id: str


@dataclass
class Finding:
    id: str
    text: str
    question_id: str


@dataclass
class Synthesis:
    id: str
    summary: str
    goal_id: str


# ---------------------------------------------------------------------------
# Internal counter
# ---------------------------------------------------------------------------

_COUNTER = 0


def _next_id(prefix: str) -> str:
    global _COUNTER
    _COUNTER += 1
    return f"{prefix}-{_COUNTER}"


# ---------------------------------------------------------------------------
# Responders
# ---------------------------------------------------------------------------

def _on_goal_created(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
    """When a Goal is created, decompose it into default sub-questions."""
    if event.data.get("type") != GOAL:
        return

    goal_id = event.data["id"]
    goal_text = event.data.get("data", {}).get("text", goal_id)

    default_angles = [
        f"What are the key facts about: {goal_text}?",
        f"What are the main risks or challenges for: {goal_text}?",
        f"What evidence supports or refutes claims about: {goal_text}?",
    ]

    for angle in default_angles:
        q_id = _next_id("question")
        q_event = make_event(
            type=OBJECT_CREATED,
            source=event.source,
            actor="research.on_goal_created",
            cause=[event.id],
            data={
                "id": q_id,
                "type": QUESTION,
                "data": {"text": angle, "goal_id": goal_id},
            },
            run_id_counter=_COUNTER,
        )
        yield q_event

        rel_id = _next_id("rel-decomposes")
        yield make_event(
            type=RELATION_CREATED,
            source=event.source,
            actor="research.on_goal_created",
            cause=[q_event.id],
            data={
                "id": rel_id,
                "type": DECOMPOSES_INTO,
                "source_id": goal_id,
                "target_id": q_id,
            },
            run_id_counter=_COUNTER,
        )


def _on_question_created(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
    """When a Question is created, emit a placeholder Finding for it."""
    if event.data.get("type") != QUESTION:
        return

    q_id = event.data["id"]
    q_text = event.data.get("data", {}).get("text", q_id)
    finding_id = _next_id("finding")

    f_event = make_event(
        type=OBJECT_CREATED,
        source=event.source,
        actor="research.on_question_created",
        cause=[event.id],
        data={
            "id": finding_id,
            "type": FINDING,
            "data": {
                "text": f"[Pending] Research needed for: {q_text}",
                "question_id": q_id,
                "status": "pending",
            },
        },
        run_id_counter=_COUNTER,
    )
    yield f_event

    rel_id = _next_id("rel-answers")
    yield make_event(
        type=RELATION_CREATED,
        source=event.source,
        actor="research.on_question_created",
        cause=[f_event.id],
        data={
            "id": rel_id,
            "type": ANSWERS,
            "source_id": finding_id,
            "target_id": q_id,
        },
        run_id_counter=_COUNTER,
    )


def _on_finding_created(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
    """When all questions for a Goal have at least one Finding, emit a Synthesis."""
    if event.data.get("type") != FINDING:
        return

    # Find the goal for this finding via its question
    finding_data = event.data.get("data", {})
    q_id = finding_data.get("question_id")
    if not q_id or q_id not in world.objects:
        return

    q_obj = world.objects[q_id]
    goal_id = q_obj.data.get("goal_id")
    if not goal_id or goal_id not in world.objects:
        return

    # Check if all questions for this goal now have findings
    goal_questions = [
        obj for obj in world.objects.values()
        if obj.type == QUESTION and obj.data.get("goal_id") == goal_id
    ]
    if not goal_questions:
        return

    question_ids = {q.id for q in goal_questions}
    covered_q_ids = {
        obj.data.get("question_id")
        for obj in world.objects.values()
        if obj.type == FINDING and obj.data.get("question_id") in question_ids
    }
    # Include the current finding (not yet in world when event fires)
    covered_q_ids.add(q_id)

    # Only synthesize once all questions are covered, and not if synthesis exists already
    existing_syntheses = [
        obj for obj in world.objects.values()
        if obj.type == SYNTHESIS and obj.data.get("goal_id") == goal_id
    ]
    if existing_syntheses or question_ids != covered_q_ids:
        return

    synth_id = _next_id("synthesis")
    goal_text = world.objects[goal_id].data.get("text", goal_id)
    s_event = make_event(
        type=OBJECT_CREATED,
        source=event.source,
        actor="research.on_finding_created",
        cause=[event.id],
        data={
            "id": synth_id,
            "type": SYNTHESIS,
            "data": {
                "summary": f"[Pending synthesis for: {goal_text}]",
                "goal_id": goal_id,
                "finding_count": len(covered_q_ids),
            },
        },
        run_id_counter=_COUNTER,
    )
    yield s_event

    rel_id = _next_id("rel-synthesizes")
    yield make_event(
        type=RELATION_CREATED,
        source=event.source,
        actor="research.on_finding_created",
        cause=[s_event.id],
        data={
            "id": rel_id,
            "type": SYNTHESIZES,
            "source_id": synth_id,
            "target_id": goal_id,
        },
        run_id_counter=_COUNTER,
    )


# ---------------------------------------------------------------------------
# Kit factory
# ---------------------------------------------------------------------------

def seed_from_goal(goal: str, run_id: str) -> list[KandoEvent]:
    """Turn a free-text goal into seed events for a research run."""
    goal_id = f"goal-{run_id[:8]}"
    return [
        KandoEvent(
            id=f"goal.created-{run_id[:8]}",
            type=OBJECT_CREATED,
            source=f"run:{run_id}",
            actor="cli",
            cause=[],
            timestamp=datetime.now(timezone.utc),
            data={"id": goal_id, "type": GOAL, "data": {"text": goal}},
        )
    ]


def create_kit() -> list[Responder]:
    """Return all responders that compose the research kit."""
    return [
        Responder(
            name="research.on_goal_created",
            pattern=frozenset({OBJECT_CREATED}),
            fn=_on_goal_created,
        ),
        Responder(
            name="research.on_question_created",
            pattern=frozenset({OBJECT_CREATED}),
            fn=_on_question_created,
        ),
        Responder(
            name="research.on_finding_created",
            pattern=frozenset({OBJECT_CREATED}),
            fn=_on_finding_created,
        ),
    ]
