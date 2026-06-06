from __future__ import annotations
# KurrentDB-backed ledger store (Phase 1).
# Placeholder — implementation forthcoming.

from typing import Iterator
from kando.schema.events import KandoEvent


class StreamLedgerStore:
    """Durable ledger backed by a KurrentDB stream."""

    def __init__(self, run_id: str, client) -> None:
        self._run_id = run_id
        self._client = client

    def append(self, events: list[KandoEvent]) -> None:
        raise NotImplementedError

    def read(self, from_position: int = 0) -> Iterator[KandoEvent]:
        raise NotImplementedError

    def read_all(self) -> Iterator[KandoEvent]:
        return self.read(from_position=0)

    def stream_name(self) -> str:
        return f"run:{self._run_id}"
