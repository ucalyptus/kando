from __future__ import annotations
import json
from pytest_bdd import scenarios, given, when, then, parsers
from kando.cache.llm import LLMCache, ScopedLLMCache

scenarios('../cache.feature')


@given('an empty LLM cache', target_fixture='cache_ctx')
def empty_llm_cache():
    return {"cache": LLMCache(), "result": None, "scoped": None}


@given('a parent cache with a stored response for {"prompt": "p"}', target_fixture='cache_ctx')
def parent_cache_with_p():
    cache = LLMCache()
    cache.put({"prompt": "p"}, "parent-response")
    return {"cache": cache, "result": None, "scoped": None}


@given('a parent cache', target_fixture='cache_ctx')
def parent_cache_empty():
    cache = LLMCache()
    return {"cache": cache, "result": None, "scoped": None}


@when(parsers.parse('I put request {req_json} with response "{response}"'))
def put_request(cache_ctx, req_json, response):
    req = json.loads(req_json)
    cache_ctx["last_request"] = req
    cache_ctx["cache"].put(req, response)


@when(parsers.parse('I get request {req_json}'))
def get_request(cache_ctx, req_json):
    req = json.loads(req_json)
    cache_ctx["last_request"] = req
    cache_ctx["result"] = cache_ctx["cache"].get(req)


@when(parsers.parse('I create a scoped cache with prefix "{prefix}"'))
def create_scoped_cache(cache_ctx, prefix):
    cache_ctx["scoped"] = cache_ctx["cache"].scope(prefix)
    cache_ctx["scoped_prefix"] = prefix


@when('I get {"prompt": "p"} from the scoped cache')
def get_from_scoped(cache_ctx):
    cache_ctx["result"] = cache_ctx["scoped"].get({"prompt": "p"})


@when('I create a scoped cache and put {"prompt": "q"} with response "branch-answer"')
def scoped_put(cache_ctx):
    scoped = cache_ctx["cache"].scope("branch-1")
    cache_ctx["scoped"] = scoped
    scoped.put({"prompt": "q"}, "branch-answer")


@then(parsers.parse('getting that request returns "{expected}"'))
def check_get_returns(cache_ctx, expected):
    result = cache_ctx["cache"].get(cache_ctx["last_request"])
    assert result == expected, f"Expected '{expected}', got '{result}'"


@then('the result is None')
def check_result_none(cache_ctx):
    assert cache_ctx["result"] is None, f"Expected None, got {cache_ctx['result']}"


@then("the result is the parent's response")
def check_result_parent_response(cache_ctx):
    assert cache_ctx["result"] == "parent-response", (
        f"Expected 'parent-response', got '{cache_ctx['result']}'"
    )


@then('the parent cache does not contain {"prompt": "q"}')
def check_parent_no_q(cache_ctx):
    result = cache_ctx["cache"].get({"prompt": "q"})
    assert result is None, f"Parent should not have 'q', got: {result}"
