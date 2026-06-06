"""Durable ledger backed by EventStoreDB via esdbclient."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Iterator

from esdbclient import EventStoreDBClient, NewEvent, StreamState
from esdbclient.exceptions import NotFound

from kando.ledger.interface import LedgerStore
from kando.schema.events import KandoEvent

_NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def _make_uri(env_url: str | None = None) -> str:
    url = (env_url or os.environ.get("EVENTSTORE_URL", "http://localhost:2113")).rstrip("/")
    if url.startswith("http://"):
        return f"esdb://{url[7:]}?tls=false"
    if url.startswith("https://"):
        return f"esdb://{url[8:]}"
    return url


def _serialize(event: KandoEvent) -> NewEvent:
    payload = {
        "id": event.id,
        "type": event.type,
        "source": event.source,
        "actor": event.actor,
        "cause": event.cause,
        "timestamp": event.timestamp.isoformat(),
        "data": event.data,
    }
    return NewEvent(
        type=event.type,
        data=json.dumps(payload).encode(),
        id=uuid.uuid5(_NS, event.id),
    )


def _deserialize(recorded: "RecordedEvent") -> KandoEvent:  # noqa: F821
    payload = json.loads(recorded.data)
    ts = payload["timestamp"]
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return KandoEvent(
        id=payload["id"],
        type=payload["type"],
        source=payload["source"],
        actor=payload["actor"],
        cause=payload["cause"],
        timestamp=datetime.fromisoformat(ts),
        data=payload["data"],
    )


class EventStreamLedgerStore(LedgerStore):
    """Durable ledger backed by an EventStoreDB stream."""

    def __init__(self, run_id: str, uri: str | None = None) -> None:
        self._run_id = run_id
        self._client = EventStoreDBClient(uri=_make_uri(uri))
        self._length: int | None = None

    # ------------------------------------------------------------------
    # LedgerStore interface
    # ------------------------------------------------------------------

    def append(self, events: list[KandoEvent]) -> int:
        if not events:
            return self._get_length()
        self._client.append_to_stream(
            self.stream_name(),
            current_version=StreamState.ANY,
            events=[_serialize(e) for e in events],
        )
        if self._length is not None:
            self._length += len(events)
        else:
            self._length = self._fetch_length()
        return self._length

    def read(self, from_position: int = 0) -> Iterator[KandoEvent]:
        if from_position is None:
            raise TypeError("from_position must be an int, got None")
        try:
            for recorded in self._client.read_stream(
                self.stream_name(),
                stream_position=from_position or None,
            ):
                if not recorded.is_system_event:
                    yield _deserialize(recorded)
        except NotFound:
            return

    def stream_name(self) -> str:
        return f"run:{self._run_id}"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_length(self) -> int:
        if self._length is None:
            self._length = self._fetch_length()
        return self._length

    def _fetch_length(self) -> int:
        """Read the last event's stream_position to determine current length."""
        try:
            tail = list(self._client.read_stream(
                self.stream_name(), backwards=True, limit=1,
            ))
            user_events = [e for e in tail if not e.is_system_event]
            return user_events[0].stream_position + 1 if user_events else 0
        except NotFound:
            return 0
