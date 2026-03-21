Feature: Query ordering
    As a developer
    I want to order query results
    So that I get documents in the right order

    Scenario: Create ascending order
        Given an Asc directive on field "population"
        Then the direction is "ASCENDING"

    Scenario: Create descending order
        Given a Desc directive on field "population"
        Then the direction is "DESCENDING"
