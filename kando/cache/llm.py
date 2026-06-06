from __future__ import annotations
import hashlib
import json
from typing import Any


class LLMCache:
    """Content-addressed cache of LLM responses keyed by normalized request hash."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    def _key(self, request: dict) -> str:
        normalized = json.dumps(request, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(normalized.encode()).hexdigest()

    def get(self, request: dict) -> Any | None:
        return self._store.get(self._key(request))

    def put(self, request: dict, response: Any) -> str:
        key = self._key(request)
        self._store[key] = response
        return key

    def scope(self, prefix: str) -> "ScopedLLMCache":
        """Return a branch-scoped cache that reads from this parent on miss."""
        return ScopedLLMCache(parent=self, prefix=prefix)

    def __len__(self) -> int:
        return len(self._store)


class ScopedLLMCache:
    """A cache scoped to a branch prefix. Writes go to own store; misses fall back to parent."""

    def __init__(self, parent: LLMCache, prefix: str) -> None:
        self._parent = parent
        self._prefix = prefix
        self._store: dict[str, Any] = {}

    def _key(self, request: dict) -> str:
        scoped = {"_scope": self._prefix, **request}
        normalized = json.dumps(scoped, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(normalized.encode()).hexdigest()

    def get(self, request: dict) -> Any | None:
        local = self._store.get(self._key(request))
        if local is not None:
            return local
        return self._parent.get(request)

    def put(self, request: dict, response: Any) -> str:
        key = self._key(request)
        self._store[key] = response
        return key

    def __len__(self) -> int:
        return len(self._store)
