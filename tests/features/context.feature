Feature: Context operations
    As a developer
    I want to query Firestore documents through an ODM context
    So that I get typed model instances

    Scenario: Get a document by ID
        Given a Firestore collection "cities" with a document "SF"
        When I call get with model City and id "SF"
        Then I receive a City instance with id "SF"

    Scenario: Get a non-existent document raises error
        Given a Firestore collection "cities" without document "NOPE"
        When I call get with model City and id "NOPE"
        Then a DocumentNotFoundError error is raised

    Scenario: Find a non-existent document returns None
        Given a Firestore collection "cities" without document "NOPE"
        When I call find with model City and id "NOPE"
        Then the result is None
