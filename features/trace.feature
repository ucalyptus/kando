Feature: Trace — causal lineage

  Scenario: Tracing an event returns its full causal chain to root
    Given a ledger with root event "e0" child "e1" caused by "e0" grandchild "e2" caused by "e1"
    When I trace event "e2"
    Then the chain contains "e2" "e1" "e0" in that order

  Scenario: Tracing a root event returns just the root
    Given a ledger with root event "e0" with no causes
    When I trace event "e0"
    Then the chain contains only "e0"

  Scenario: Explain returns KandoEvent objects not just IDs
    Given a chain of events e0 then e1 caused by e0 then e2 caused by e1
    When I call explain for "e2"
    Then the result is a list of KandoEvent instances
