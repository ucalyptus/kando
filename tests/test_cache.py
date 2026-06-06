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
