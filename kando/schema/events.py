from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class KandoEvent:
    id: str                          # unique, monotonic within the ledger
    type: str                        # e.g. "object.created", "responder.fired"
    source: str                      # ledger identity (run:{id} or branch:{id})
    actor: str                       # which responder emitted this event
    cause: list[str]                 # parent event IDs — the causal chain
    timestamp: datetime              # wall-clock time of emission
    data: dict[str, Any] = field(default_factory=dict)


# Fixed event type registry
OBJECT_CREATED      = "object.created"
OBJECT_PATCHED      = "object.patched"
RELATION_CREATED    = "relation.created"
RELATION_REMOVED    = "relation.removed"
RESPONDER_FIRED     = "responder.fired"
RESPONDER_COMPLETED = "responder.completed"
RESPONDER_FAILED    = "responder.failed"
LLM_REQUEST         = "llm.request"
LLM_RESPONSE        = "llm.response"
TOOL_CALLED         = "tool.called"
TOOL_RETURNED       = "tool.returned"
BRANCH_CREATED      = "branch.created"
BUDGET_EXHAUSTED    = "budget.exhausted"
KIT_LOADED          = "kit.loaded"
