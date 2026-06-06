Feature: LLM Cache — content-addressed response store

  Scenario: Putting a response and getting it back
    Given an empty LLM cache
    When I put request {"model": "x", "prompt": "hello"} with response "world"
    Then getting that request returns "world"

  Scenario: A cache miss returns None
    Given an empty LLM cache
    When I get request {"model": "x", "prompt": "unknown"}
    Then the result is None

  Scenario: Scoped cache reads from parent on miss
    Given a parent cache with a stored response for {"prompt": "p"}
    When I create a scoped cache with prefix "branch-1"
    And I get {"prompt": "p"} from the scoped cache
    Then the result is the parent's response

  Scenario: Scoped cache writes do not affect the parent
    Given a parent cache
    When I create a scoped cache and put {"prompt": "q"} with response "branch-answer"
    Then the parent cache does not contain {"prompt": "q"}
