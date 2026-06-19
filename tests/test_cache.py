"""Tests for LLMCache: put/get, cache miss, scoped cache."""
import pytest
from kando.cache.llm import LLMCache, ScopedLLMCache


# ---------------------------------------------------------------------------
# LLMCache basics
# ---------------------------------------------------------------------------

def test_put_and_get():
    cache = LLMCache()
    request = {"model": "gpt-4", "prompt": "hello"}
    response = {"text": "world"}
    cache.put(request, response)
    assert cache.get(request) == response


def test_cache_miss_returns_none():
    cache = LLMCache()
    assert cache.get({"prompt": "unknown"}) is None


def test_cache_length():
    cache = LLMCache()
    cache.put({"a": 1}, "resp-a")
    cache.put({"b": 2}, "resp-b")
    assert len(cache) == 2


def test_cache_key_is_order_independent():
    cache = LLMCache()
    cache.put({"a": 1, "b": 2}, "result")
    assert cache.get({"b": 2, "a": 1}) == "result"


def test_different_requests_dont_collide():
    cache = LLMCache()
    cache.put({"prompt": "foo"}, "foo-resp")
    cache.put({"prompt": "bar"}, "bar-resp")
    assert cache.get({"prompt": "foo"}) == "foo-resp"
    assert cache.get({"prompt": "bar"}) == "bar-resp"


# ---------------------------------------------------------------------------
# ScopedLLMCache: reads parent on miss, writes locally
# ---------------------------------------------------------------------------

def test_scoped_cache_reads_parent_on_miss():
    parent = LLMCache()
    parent.put({"q": "shared"}, "shared-response")
    scoped = parent.scope("branch-1")
    assert scoped.get({"q": "shared"}) == "shared-response"


def test_scoped_cache_local_write_does_not_affect_parent():
    parent = LLMCache()
    scoped = parent.scope("branch-1")
    scoped.put({"q": "local"}, "local-response")
    assert parent.get({"q": "local"}) is None


def test_scoped_cache_local_hit_shadows_parent():
    parent = LLMCache()
    parent.put({"q": "both"}, "parent-response")
    scoped = parent.scope("branch-1")
    scoped.put({"q": "both"}, "local-response")
    assert scoped.get({"q": "both"}) == "local-response"


def test_scoped_cache_miss_returns_none():
    parent = LLMCache()
    scoped = parent.scope("branch-x")
    assert scoped.get({"q": "nonexistent"}) is None


def test_scoped_cache_length_counts_only_local():
    parent = LLMCache()
    parent.put({"q": "parent"}, "resp")
    scoped = parent.scope("branch-1")
    scoped.put({"q": "child"}, "child-resp")
    assert len(scoped) == 1


# ---------------------------------------------------------------------------
# LRU eviction tests
# ---------------------------------------------------------------------------

def test_llm_cache_lru_eviction():
    cache = LLMCache(max_entries=3)
    for i in range(4):
        cache.put({"q": str(i)}, f"resp-{i}")
    # First entry (q=0) should be evicted
    assert cache.get({"q": "0"}) is None
    assert cache.get({"q": "3"}) == "resp-3"
    assert len(cache) == 3


def test_llm_cache_lru_order():
    cache = LLMCache(max_entries=3)
    for i in range(3):
        cache.put({"q": str(i)}, f"resp-{i}")
    # Access q=0 to promote it
    cache.get({"q": "0"})
    # Add q=3 — q=1 (least recently used) should be evicted, not q=0
    cache.put({"q": "3"}, "resp-3")
    assert cache.get({"q": "0"}) == "resp-0"
    assert cache.get({"q": "1"}) is None


# ---------------------------------------------------------------------------
# ScopedLLMCache: isolation invariants (regression fence, issue #15)
# ---------------------------------------------------------------------------

def test_scoped_cache_write_not_visible_to_parent():
    """Writing to a scoped cache must NOT leak to the parent."""
    parent = LLMCache()
    scope = parent.scope("branch-A")
    scope.put({"q": "hello"}, "response-A")
    # Parent should have a miss — scoped writes are isolated
    assert parent.get({"q": "hello"}) is None


def test_scoped_cache_sibling_isolation():
    """Two sibling scopes sharing a parent must not see each other's writes."""
    parent = LLMCache()
    scope_a = parent.scope("branch-A")
    scope_b = parent.scope("branch-B")
    scope_a.put({"q": "hello"}, "response-A")
    # Scope B should not see scope A's write (different prefix -> different key)
    assert scope_b.get({"q": "hello"}) is None


def test_scoped_cache_parent_hit_visible_to_scope():
    """Parent cache hits must be visible to child scopes via fallback."""
    parent = LLMCache()
    parent.put({"q": "shared"}, "shared-response")
    scope = parent.scope("branch-A")
    # Scope should find parent's value via fallback
    assert scope.get({"q": "shared"}) == "shared-response"


def test_two_siblings_no_implicit_promotion():
    """A put() on scoped cache must not promote to parent so sibling stays blind."""
    parent = LLMCache()
    scope_a = parent.scope("branch-A")
    scope_b = parent.scope("branch-B")
    scope_a.put({"q": "unique"}, "from-A")
    # Parent still misses — no promotion happened
    assert parent.get({"q": "unique"}) is None
    # Scope B also misses — can't see A's write
    assert scope_b.get({"q": "unique"}) is None
