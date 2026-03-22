Feature: Document metadata and optimistic locking
    As a developer
    I want to track document metadata and use optimistic locking
    So that I can detect and prevent conflicting writes

    Scenario: Metadata is populated after reading a document
        Given a City document "SF" with update_time in Firestore
        When I read it with ctx.get
        Then get_metadata returns the update_time

    Scenario: Metadata is populated after saving a document
        Given a City instance with id "SF"
        When I save it and Firestore returns a WriteResult
        Then get_metadata returns the new update_time

    Scenario: Metadata is cleared after deleting a document
        Given a City instance with id "SF" and metadata
        When I delete the instance
        Then get_metadata raises CendryError

    Scenario: Update with if_unchanged passes precondition
        Given a City instance with id "SF" and metadata
        When I update with if_unchanged=True
        Then the update passes with a LastUpdateOption

    Scenario: Untracked instance with if_unchanged raises error
        Given a City instance with id "SF" without metadata
        When I update with if_unchanged=True
        Then a CendryError is raised with message "No metadata"
