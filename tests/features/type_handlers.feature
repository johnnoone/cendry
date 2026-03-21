Feature: Type handlers
    As a developer
    I want to register custom type handlers
    So that my types are auto-converted to/from Firestore

    Scenario: Register type with handler class
        Given a custom type with a handler
        When I define a model with that type
        Then the model is created successfully

    Scenario: Register type with kwargs
        Given a custom type registered with deserialize kwarg
        When I deserialize a document with that type
        Then the value is converted by the handler

    Scenario: Serialize without deserialize raises
        When I register a type with serialize but no deserialize
        Then ValueError is raised

    Scenario: Handler and kwargs are mutually exclusive
        When I register a type with both handler and kwargs
        Then ValueError is raised

    Scenario: Container of handled type
        Given a custom type registered with a handler
        When I deserialize a list of that type
        Then each element is converted by the handler
