Feature: Batch writes
    As a developer
    I want to write multiple documents atomically
    So that I can ensure consistency across related changes

    Scenario: Save many documents atomically
        Given 3 City instances with ids
        When I save them all with save_many
        Then all 3 documents are written to Firestore

    Scenario: Save many over 500 raises error
        Given 501 City instances with ids
        When I save them all with save_many
        Then a CendryError is raised with message "Batch limit exceeded"

    Scenario: Delete many documents by instances
        Given 3 City instances with ids
        When I delete them all with delete_many
        Then all 3 documents are deleted from Firestore

    Scenario: Batch context manager commits on exit
        Given a batch context manager
        When I save a City inside the batch
        Then the batch commits on exit

    Scenario: Batch context manager does not commit on exception
        Given a batch context manager
        When an exception occurs inside the batch
        Then the batch does not commit
