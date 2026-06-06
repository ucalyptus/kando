Feature: Runtime — event loop

  Scenario: Seed events are committed to the ledger and applied to the world
    Given a runtime with an empty ledger and no responders
    When I run with a seed object.created event for "goal-1"
    Then the ledger contains 1 event
    And the world contains object "goal-1"

  Scenario: A matching responder fires and its output is processed
    Given a runtime with a responder that emits a child event on object.created
    When I run with a seed object.created event for "parent"
    Then the world contains object "parent"
    And the world contains the child object emitted by the responder

  Scenario: Budget exhaustion halts the loop
    Given a runtime with a budget of max_events=2
    When I run with a seed event that triggers a responder that emits 10 events
    Then a budget.exhausted event is in the ledger
    And the world does not grow beyond the budget

  Scenario: Permissive replay reproduces the same world as direct projection
    Given a ledger with committed events
    When I call replay with strict False
    Then the resulting world matches direct projection of the ledger
