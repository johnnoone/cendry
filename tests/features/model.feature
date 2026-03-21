Feature: Model definition
    As a developer
    I want to define Firestore document models
    So that I can work with typed data

    Scenario: Define a model with a collection
        Given a model class "City" with collection "cities"
        Then the model has collection "cities"
        And the model has an "id" field

    Scenario: Model requires a collection
        When I define a model without a collection
        Then a TypeError is raised

    Scenario: Define an embedded map
        Given a map class "Mayor" with fields "name" and "since"
        Then the map has no "id" field
        And the map is a dataclass

    Scenario: Model cannot nest another model
        Given a model class "City" with collection "cities"
        When I define a model that nests "City"
        Then a TypeError is raised with message containing "cannot nest"
