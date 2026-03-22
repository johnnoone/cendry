Feature: CRUD operations against Firestore
    As a developer
    I want to perform CRUD operations through Cendry
    So that I can persist and retrieve typed model instances from a real Firestore

    Scenario: Save and retrieve a document
        Given a Cendry context connected to the emulator
        When I save a City with name "San Francisco" and population 870000
        Then the City has an auto-generated ID
        And I can retrieve it by ID with matching fields

    Scenario: Save overwrites an existing document
        Given a saved City "SF" with population 870000
        When I update its population to 900000 and save again
        Then retrieving "SF" shows population 900000

    Scenario: Create a duplicate raises DocumentAlreadyExistsError
        Given a saved City "SF" with population 870000
        When I create another City with ID "SF"
        Then a DocumentAlreadyExistsError is raised

    Scenario: Partial update changes only specified fields
        Given a saved City "SF" with population 870000
        When I update population to 900000
        Then retrieving "SF" shows population 900000
        And the name is still "San Francisco"

    Scenario: Delete removes the document
        Given a saved City "SF" with population 870000
        When I delete it
        Then finding "SF" returns None

    Scenario: Refresh re-fetches from Firestore
        Given a saved City "SF" with population 870000
        When another client changes population to 999
        And I refresh the instance
        Then the instance population is 999

    Scenario: Metadata is populated on read
        Given a saved City "SF" with population 870000
        When I read it with ctx.get
        Then get_metadata returns update_time and create_time
