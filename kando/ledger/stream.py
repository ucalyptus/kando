from __future__ import annotations
from typing import Any, Iterator
from kando.schema.events import KandoEvent


class EventStreamLedgerStore:
    """Durable ledger backed by an append-only event stream. Backend-agnostic placeholder."""

    def __init__(self, run_id: str, backend: Any) -> None:
        self._run_id = run_id
        self._backend = backend

    def append(self, events: list[KandoEvent]) -> int:
        raise NotImplementedError

    def read(self, from_position: int = 0) -> Iterator[KandoEvent]:
        raise NotImplementedError

    def read_all(self) -> Iterator[KandoEvent]:
        return self.read(from_position=0)

    def stream_name(self) -> str:
        return f"run:{self._run_id}"
