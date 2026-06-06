Feature: World — deterministic projected state

  Scenario: Creating an object adds it to the world
    Given an empty world
    When an object.created event is applied with id "obj-1" type "claim" data {"text": "hello"}
    Then the world contains object "obj-1"
    And "obj-1" has data {"text": "hello"}

  Scenario: Patching an object updates its data
    Given a world with object "obj-1" of type "claim" with data {"text": "hello"}
    When an object.patched event is applied with id "obj-1" patch {"text": "world"}
    Then "obj-1" has data {"text": "world"}

  Scenario: Patching a non-existent object is a no-op
    Given an empty world
    When an object.patched event is applied with id "ghost" patch {"x": 1}
    Then the world contains no objects

  Scenario: Removing a relation removes it from the world
    Given a world with relation "rel-1" of type "supports" between "a" and "b"
    When a relation.removed event is applied with id "rel-1"
    Then the world contains no relations

  Scenario: Projection is deterministic across multiple runs
    Given a fixed sequence of 5 events
    When I project those events 3 times
    Then all 3 resulting worlds are identical
