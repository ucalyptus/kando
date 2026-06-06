Feature: Ledger — append-only event log

  Scenario: Appending events increases the ledger position
    Given an empty in-memory ledger for run "test-run"
    When I append 3 events
    Then the returned position is 3
    And reading all events yields 3 events

  Scenario: Reading from a position returns only events after that position
    Given a ledger with 10 events
    When I read from position 5
    Then I receive exactly 5 events
    And the first event has index 5

  Scenario: Stream name includes the run ID
    Given a ledger for run "abc-123"
    Then the stream name is "run:abc-123"
