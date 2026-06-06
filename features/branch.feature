Feature: Branch — fork and diff

  Scenario: A fork records the parent run and fork position
    Given a run "run-001" with 500 events
    When I fork at position 250 creating "branch-001"
    Then branch metadata has parent_run_id "run-001"
    And branch metadata has fork_position 250

  Scenario: Diffing identical worlds reports no changes
    Given two identical worlds with the same objects and relations
    When I diff them
    Then the diff is empty

  Scenario: Diffing worlds with a new object reports it as added
    Given world A with no objects
    And world B with object "new-obj"
    When I diff A against B
    Then added_objects contains "new-obj"

  Scenario: WorldDiff summary describes changes concisely
    Given a diff with 2 added objects and 1 removed relation
    When I call summary
    Then the result is "+2 objects, -1 relations"
