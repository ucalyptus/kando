from __future__ import annotations
from typing import Iterator
from kando.ledger.interface import LedgerStore
from kando.schema.events import KandoEvent


class MemoryLedgerStore(LedgerStore):
    """In-process ledger for testing — no persistence."""

    def __init__(self, run_id: str) -> None:
        self._run_id = run_id
        self._events: list[KandoEvent] = []

    def append(self, events: list[KandoEvent]) -> int:
        self._events.extend(events)
        return len(self._events)

    def read(self, from_position: int = 0) -> Iterator[KandoEvent]:
        yield from self._events[from_position:]

    def stream_name(self) -> str:
        return f"run:{self._run_id}"
