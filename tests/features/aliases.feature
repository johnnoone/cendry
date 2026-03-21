Feature: Field aliases
    As a developer
    I want fields to map to different Firestore names
    So that Python names can differ from Firestore names

    Scenario: Field with alias uses alias in filter
        Given a model with field "name" aliased to "displayName"
        When I create a filter with the field equal to "SF"
        Then the filter uses "displayName" as the field name

    Scenario: to_dict uses Python names by default
        Given a model instance with aliased field "name" set to "SF"
        When I call to_dict
        Then the key is "name"

    Scenario: to_dict uses alias when by_alias is True
        Given a model instance with aliased field "name" set to "SF"
        When I call to_dict with by_alias=True
        Then the key is "displayName"

    Scenario: from_dict uses Python names by default
        Given a dict with key "name" set to "SF"
        When I call from_dict
        Then the model field "name" is "SF"

    Scenario: from_dict uses alias when by_alias is True
        Given a dict with key "displayName" set to "SF"
        When I call from_dict with by_alias=True
        Then the model field "name" is "SF"
