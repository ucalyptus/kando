from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Iterator
from kando.schema.events import KandoEvent


class LedgerStore(ABC):
    """Abstract base for all ledger backends. High-level modules depend on this, not concretions."""

    @abstractmethod
    def append(self, events: list[KandoEvent]) -> int:
        """Append events and return the new total position (length of ledger after append)."""
        ...

    @abstractmethod
    def read(self, from_position: int = 0) -> Iterator[KandoEvent]:
        """Yield events starting at from_position."""
        ...

    @abstractmethod
    def stream_name(self) -> str:
        """Return the stream identity for this ledger (e.g. 'run:abc-123')."""
        ...

    def read_all(self) -> Iterator[KandoEvent]:
        """Yield all events from the beginning."""
        return self.read(from_position=0)
