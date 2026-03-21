Feature: Query object
    As a developer
    I want a chainable query API
    So that I can build queries fluently

    Scenario: select returns a Query
        When I call select on a model
        Then I get a Query object

    Scenario: filter returns a new Query
        When I call select and filter
        Then I get a new Query object

    Scenario: order_by returns a new Query
        When I call select and order_by
        Then I get a new Query object

    Scenario: limit returns a new Query
        When I call select and limit
        Then I get a new Query object

    Scenario: to_list fetches results
        When I call select and to_list with documents
        Then I get a non-empty list

    Scenario: first with results returns instance
        When I call select and first with documents
        Then I get an instance

    Scenario: first without results returns None
        When I call select and first without documents
        Then I get None

    Scenario: exists with results returns True
        When I call select and exists with documents
        Then I get True

    Scenario: exists without results returns False
        When I call select and exists without documents
        Then I get False
