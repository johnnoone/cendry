Feature: Query filters
    As a developer
    I want to filter Firestore queries
    So that I can retrieve specific documents

    Scenario: Create a field filter
        Given a FieldFilter with field "state", operator "==" and value "CA"
        Then the filter is a valid Firestore FieldFilter

    Scenario: Compose filters with AND
        Given two field filters
        When I combine them with And
        Then the result is a composite filter

    Scenario: Compose filters with OR
        Given two field filters
        When I combine them with Or
        Then the result is a composite filter

    Scenario: Field descriptor produces a filter
        Given a model with a "state" field
        When I call eq("CA") on the field descriptor
        Then the result is a filter with operator "=="
