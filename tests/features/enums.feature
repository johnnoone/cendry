Feature: Enum support
    As a developer
    I want enum fields auto-converted
    So that I work with Python enums, not raw strings

    Scenario: Enum deserializes by value
        Given a model with enum field stored by value
        When I deserialize a document with value "active"
        Then the field is Status.ACTIVE

    Scenario: Enum deserializes by name
        Given a model with enum field stored by name
        When I deserialize a document with value "ADMIN"
        Then the field is Role.ADMIN

    Scenario: Enum serializes by value
        Given a model instance with enum Status.INACTIVE
        When I call to_dict
        Then the value is "inactive"

    Scenario: Enum serializes by name
        Given a model instance with enum Role.USER stored by name
        When I call to_dict
        Then the value is "USER"
