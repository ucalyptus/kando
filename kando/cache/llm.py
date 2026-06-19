from __future__ import annotations
import hashlib
import json
from collections import OrderedDict
from typing import Any


class LLMCache:
    """Content-addressed cache of LLM responses keyed by normalized request hash.

    Uses an LRU eviction policy backed by ``collections.OrderedDict`` so the
    cache never grows beyond *max_entries* entries.
    """

    def __init__(self, max_entries: int = 2048) -> None:
        self._store: OrderedDict[str, Any] = OrderedDict()
        self._max_entries = max_entries

    def _key(self, request: dict) -> str:
        normalized = json.dumps(request, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(normalized.encode()).hexdigest()

    def get(self, request: dict) -> Any | None:
        key = self._key(request)
        if key not in self._store:
            return None
        self._store.move_to_end(key)
        return self._store[key]

    def put(self, request: dict, response: Any) -> str:
        key = self._key(request)
        self._store[key] = response
        self._store.move_to_end(key)
        while len(self._store) > self._max_entries:
            self._store.popitem(last=False)
        return key

    def scope(self, prefix: str) -> "ScopedLLMCache":
        """Return a branch-scoped cache that reads from this parent on miss."""
        return ScopedLLMCache(parent=self, prefix=prefix)

    def __len__(self) -> int:
        return len(self._store)


class ScopedLLMCache:
    """A cache scoped to a branch prefix. Writes go to own store; misses fall back to parent.

    Uses the same LRU eviction policy as ``LLMCache`` — bounded by *max_entries*.
    """

    def __init__(self, parent: LLMCache, prefix: str, max_entries: int = 2048) -> None:
        self._parent = parent
        self._prefix = prefix
        self._store: OrderedDict[str, Any] = OrderedDict()
        self._max_entries = max_entries

    def _key(self, request: dict) -> str:
        scoped = {"_scope": self._prefix, **request}
        normalized = json.dumps(scoped, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(normalized.encode()).hexdigest()

    def get(self, request: dict) -> Any | None:
        key = self._key(request)
        if key in self._store:
            self._store.move_to_end(key)
            return self._store[key]
        return self._parent.get(request)

    def put(self, request: dict, response: Any) -> str:
        key = self._key(request)
        self._store[key] = response
        self._store.move_to_end(key)
        while len(self._store) > self._max_entries:
            self._store.popitem(last=False)
        return key

    def __len__(self) -> int:
        return len(self._store)
