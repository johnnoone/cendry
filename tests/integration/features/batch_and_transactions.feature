Feature: Batch writes and transactions against Firestore
    As a developer
    I want to perform atomic multi-document operations
    So that I can ensure consistency across related changes

    Scenario: Save many documents atomically
        Given a Cendry context connected to the emulator
        When I save 3 cities with save_many
        Then all 3 cities are retrievable

    Scenario: Delete many documents
        Given 2 saved cities
        When I delete them with delete_many
        Then none of them are retrievable

    Scenario: Batch with mixed operations
        Given a saved City "keep" and a saved City "remove"
        When I batch-save a new City "new" and batch-delete "remove"
        Then "keep" exists
        And "new" exists
        And "remove" does not exist

    Scenario: Transaction transfers population atomically
        Given a saved City "SF" with population 1000
        And a saved City "LA" with population 2000
        When I transfer 100 population from "SF" to "LA" in a transaction
        Then "SF" has population 900
        And "LA" has population 2100

    Scenario: Transaction rolls back on exception
        Given a saved City "SF" with population 100
        When a transaction raises an exception after queuing an update
        Then "SF" still has population 100
