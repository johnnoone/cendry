Feature: Write operations
    As a developer
    I want to save, create, and delete Firestore documents through the ODM
    So that I can persist typed model instances

    Scenario: Save a document with an explicit ID
        Given a City instance with id "SF"
        When I save the instance
        Then the document is written to Firestore
        And the returned ID is "SF"

    Scenario: Save a document with auto-generated ID
        Given a City instance without an id
        When I save the instance
        Then the instance id is set to the generated value
        And the returned ID matches the generated value

    Scenario: Create a document successfully
        Given a City instance with id "SF"
        When I create the instance
        Then the document is created in Firestore
        And the returned ID is "SF"

    Scenario: Create a duplicate document raises error
        Given a City instance with id "SF"
        And the document already exists in Firestore
        When I create the instance
        Then a DocumentAlreadyExistsError is raised

    Scenario: Delete a document by instance
        Given a City instance with id "SF"
        When I delete the instance
        Then the document is deleted from Firestore

    Scenario: Delete a document with id None raises error
        Given a City instance without an id
        When I delete the instance
        Then a CendryError is raised with message "Cannot delete a model instance with id=None"

    Scenario: Delete by class and ID with must_exist on missing doc
        Given a Firestore collection without document "NOPE"
        When I delete City with id "NOPE" and must_exist is true
        Then a DocumentNotFoundError is raised
