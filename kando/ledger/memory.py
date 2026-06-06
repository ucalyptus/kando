from __future__ import annotations
from typing import Iterator
from kando.schema.events import KandoEvent


class MemoryLedgerStore:
    """In-process ledger for testing — no persistence."""

    def __init__(self, run_id: str) -> None:
        self._run_id = run_id
        self._events: list[KandoEvent] = []

    def append(self, events: list[KandoEvent]) -> None:
        self._events.extend(events)

    def read(self, from_position: int = 0) -> Iterator[KandoEvent]:
        yield from self._events[from_position:]

    def read_all(self) -> Iterator[KandoEvent]:
        yield from self._events

    def stream_name(self) -> str:
        return f"run:{self._run_id}"
