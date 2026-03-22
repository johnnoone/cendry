Feature: Transactions
    As a developer
    I want to perform atomic read-then-write operations
    So that I can avoid race conditions

    Scenario: Transaction context manager reads and writes
        Given a City document "SF" in Firestore
        When I read and update it in a transaction context manager
        Then the read returns the document
        And the update is queued

    Scenario: Transaction context manager rolls back on exception
        Given a City document "SF" in Firestore
        When an exception occurs inside the transaction
        Then the transaction rolls back

    Scenario: Transaction get on missing document raises error
        Given an empty Firestore collection
        When I get a missing document in a transaction
        Then a DocumentNotFoundError is raised

    Scenario: Transaction find on missing document returns None
        Given an empty Firestore collection
        When I find a missing document in a transaction
        Then the result is None
