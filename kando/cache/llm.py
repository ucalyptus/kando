from __future__ import annotations
import hashlib, json
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

    def __len__(self) -> int:
        return len(self._store)
