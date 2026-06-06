Feature: World — Deterministic Projected State
  The World is the live view of a kando run derived solely from the event ledger.
  It is never stored directly; it is always reconstructable by replaying events.
  All scenarios are expressed in terms of observable world state.

  Background:
    Given an empty world

  # ─────────────────────────────────────────────────────────────
  # HAPPY PATH
  # ─────────────────────────────────────────────────────────────

  @ac-1
  Scenario: Creating an object adds it to the world
    When an object.created event is applied with id "obj-1" type "claim" data {"text": "hello"}
    Then the world contains object "obj-1"
    And "obj-1" has data {"text": "hello"}

  @ac-2
  Scenario: Patching an object merges new values into its existing data
    Given a world with object "obj-1" of type "claim" with data {"a": 1, "b": 2}
    When an object.patched event is applied with id "obj-1" patch {"b": 99, "c": 3}
    Then "obj-1" has data {"a": 1, "b": 99, "c": 3}

  @ac-3
  Scenario: Creating a relation adds it to the world with its endpoint ids
    When a relation.created event is applied with id "rel-1" type "supports" from "src" to "tgt"
    Then the world contains relation "rel-1" of type "supports" from "src" to "tgt"
    And "rel-1" appears in relations for object "src"
    And "rel-1" appears in relations for object "tgt"

  @ac-4
  Scenario: Removing a relation removes it from the world
    Given a world with relation "rel-1" of type "supports" between "a" and "b"
    When a relation.removed event is applied with id "rel-1"
    Then the world contains no relations

  @ac-5
  Scenario: Budget exhaustion is recorded in the world context
    When a budget.exhausted event is applied
    Then the world context shows budget exhausted

  @ac-6
  Scenario: Projecting an event stream produces a world reflecting all events
    When I project a stream that creates "obj-a" of type "claim" then "obj-b" of type "task" then a "supports" relation from "obj-a" to "obj-b"
    Then the world contains object "obj-a"
    And the world contains object "obj-b"
    And the world contains a "supports" relation from "obj-a" to "obj-b"

  @ac-7
  Scenario: Applying an event in-place mutates the world
    When an object.created event is applied with id "obj-1" type "claim" data {}
    Then the world contains object "obj-1"

  @ac-8
  Scenario: Reprojecting from a ledger store rebuilds the world
    Given a ledger store containing events that created "obj-a" of type "claim" and "obj-b" of type "task"
    When I reproject from the ledger store
    Then the world contains object "obj-a"
    And the world contains object "obj-b"

  @ac-9
  Scenario: Looking up an existing object returns it
    Given a world with object "obj-1" of type "claim" with data {"x": 1}
    When I look up object "obj-1"
    Then I get back an object of type "claim" with data {"x": 1}

  @ac-9
  Scenario: Looking up an absent object returns nothing
    When I look up object "missing-id"
    Then the object lookup returns nothing

  @ac-10
  Scenario: Looking up relations for an object returns all touching relations
    Given a world with relation "rel-1" of type "supports" between "a" and "b"
    And relation "rel-2" of type "blocks" between "b" and "c" is also in the world
    When I look up relations for object "b"
    Then I get back 2 relations

  @ac-10
  Scenario: Relation lookup filtered by type returns only matching relations
    Given a world with relation "rel-1" of type "supports" between "a" and "b"
    And relation "rel-2" of type "blocks" between "a" and "b" is also in the world
    When I look up relations for object "a" of type "supports"
    Then I get back 1 relation of type "supports"

  @ac-11
  Scenario: A world checkpoint roundtrips all objects relations and position
    Given a world with object "obj-1" of type "claim" with data {"score": 42}
    And relation "rel-1" of type "supports" between "obj-1" and "obj-2" is also in the world
    When I save the world as run "run-abc" at ledger position 5
    And I reload the snapshot for run "run-abc"
    Then the restored world contains object "obj-1" with data {"score": 42}
    And the restored world contains relation "rel-1" of type "supports"
    And the restored ledger position is 5

  @ac-12
  Scenario: Snapshot directory is controlled by an environment variable
    Given the snapshot directory is set to a custom path via KANDO_SNAPSHOT_DIR
    When I save the world as run "run-env" at ledger position 0
    Then the snapshot file exists under the custom path

  # ─────────────────────────────────────────────────────────────
  # EDGE CASES
  # ─────────────────────────────────────────────────────────────

  @ac-13
  Scenario: Loading a snapshot for a run that was never saved returns nothing
    When I reload the snapshot for run "never-saved"
    Then the snapshot load returns nothing

  @ac-14
  Scenario: Saving a snapshot creates the directory if it does not exist
    Given the snapshot directory does not exist
    When I save the world as run "run-mkdir" at ledger position 0
    Then the snapshot directory exists

  @ac-15
  Scenario: Saving a snapshot twice for the same run replaces the first
    Given a world with object "obj-old" of type "claim" with data {}
    When I save the world as run "run-ow" at ledger position 1
    And the world is replaced by one containing object "obj-new" of type "claim" with data {}
    And I save the world as run "run-ow" at ledger position 2
    And I reload the snapshot for run "run-ow"
    Then the restored world contains object "obj-new"
    And the restored world does not contain object "obj-old"
    And the restored ledger position is 2

  @ac-16
  Scenario: Creating an object for an existing id replaces the previous object
    Given a world with object "obj-1" of type "claim" with data {"v": 1}
    When an object.created event is applied with id "obj-1" type "task" data {"v": 2}
    Then "obj-1" has type "task"
    And "obj-1" has data {"v": 2}

  @ac-17
  Scenario: Patching a non-existent object is a no-op
    When an object.patched event is applied with id "ghost" patch {"x": 1}
    Then the world contains no objects

  @ac-18
  Scenario: Removing a non-existent relation is a no-op
    When a relation.removed event is applied with id "ghost-rel"
    Then the world contains no relations

  @ac-19
  Scenario: A relation may reference objects that do not yet exist in the world
    When a relation.created event is applied with id "rel-1" type "supports" from "a" to "b"
    Then the world contains relation "rel-1"
    And the world contains no objects

  @ac-20
  Scenario: Projecting an empty event stream produces an empty world
    When I project an empty event stream
    Then the world contains no objects
    And the world contains no relations

  @ac-21
  Scenario: An object.created event with no data field stores an empty data dict
    When an object.created event is applied with id "obj-1" type "claim" and no data field
    Then "obj-1" has data {}

  @ac-21
  Scenario: A relation.created event with no data field stores an empty data dict
    When a relation.created event is applied with id "rel-1" type "supports" from "a" to "b" and no data field
    Then relation "rel-1" has data {}

  # ─────────────────────────────────────────────────────────────
  # DETERMINISM + ISOLATION
  # ─────────────────────────────────────────────────────────────

  @ac-22
  Scenario: Projecting the same event sequence multiple times gives identical worlds
    Given a fixed sequence of 5 events
    When I project those events 3 times
    Then all 3 resulting worlds are identical

  @ac-23
  Scenario: Order of independent creation events does not affect the projected world
    When I project 5 distinct object-creation events in forward order
    And I project the same 5 events in reverse order
    Then both resulting worlds contain the same objects

  @ac-24
  Scenario: Object data in the world matches the creation event exactly
    When an object.created event is applied with id "obj-1" type "claim" data {"key": "value", "num": 42}
    Then "obj-1" has data {"key": "value", "num": 42}

  @ac-25
  Scenario: Mutating event data after apply does not corrupt the world
    Given an object.created event payload for id "obj-1" type "claim" data {"v": 1}
    When I apply that event then mutate the event data to {"v": 999}
    Then "obj-1" has data {"v": 1}

  # ─────────────────────────────────────────────────────────────
  # ERRORS
  # ─────────────────────────────────────────────────────────────

  @ac-26
  Scenario: Unknown event types are silently skipped
    When an event of type "responder.fired" is applied
    Then the world contains no objects
    And the world contains no relations

  @ac-27
  Scenario: Loading a corrupt snapshot file returns nothing
    Given a snapshot file exists for run "bad-run" but contains malformed JSON
    When I reload the snapshot for run "bad-run"
    Then the snapshot load returns nothing

  # ─────────────────────────────────────────────────────────────
  # CROSS-CUTTING
  # ─────────────────────────────────────────────────────────────

  @ac-28
  Scenario: World context is not preserved in snapshots
    When a budget.exhausted event is applied
    And I save the world as run "run-ctx" at ledger position 1
    And I reload the snapshot for run "run-ctx"
    Then the restored world context does not show budget exhausted

  @ac-29
  Scenario: Snapshots for different run ids are stored independently
    When I save the world as run "run-a" at ledger position 1
    And I save the world as run "run-b" at ledger position 2
    Then the snapshot for "run-a" exists
    And the snapshot for "run-b" exists

  @ac-30
  Scenario: Snapshot file is valid JSON with the expected structure
    Given a world with object "obj-1" of type "claim" with data {}
    When I save the world as run "run-json" at ledger position 4
    Then the snapshot file for "run-json" is valid JSON
    And it has a "world" key containing "objects" and "relations" lists
    And it has a "position" integer equal to 4

  @ac-31
  Scenario: An empty world can be saved and reloaded cleanly
    When I save the world as run "run-empty" at ledger position 0
    And I reload the snapshot for run "run-empty"
    Then the restored world contains no objects
    And the restored world contains no relations
    And the restored ledger position is 0
