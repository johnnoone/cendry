Feature: Field type validation
    As a developer
    I want invalid Firestore types rejected at class definition
    So that I catch type errors early

    Scenario Outline: Valid scalar types are accepted
        When I define a model with a field of type "<type>"
        Then the model is created successfully

        Examples:
            | type     |
            | str      |
            | int      |
            | float    |
            | bool     |
            | bytes    |
            | Decimal  |
            | datetime |

    Scenario Outline: Firestore SDK types are accepted
        When I define a model with a field of type "<type>"
        Then the model is created successfully

        Examples:
            | type              |
            | GeoPoint          |
            | DocumentReference |

    Scenario: Invalid scalar type is rejected
        When I define a model with a field of type "complex"
        Then a TypeError is raised with message containing "complex"

    Scenario: Optional valid type is accepted
        When I define a model with a field of type "str | None"
        Then the model is created successfully

    Scenario: Optional invalid type is rejected
        When I define a model with a field of type "complex | None"
        Then a TypeError is raised with message containing "complex"

    Scenario: List of valid type is accepted
        When I define a model with a field of type "list[str]"
        Then the model is created successfully

    Scenario: List of invalid type is rejected
        When I define a model with a field of type "list[complex]"
        Then a TypeError is raised with message containing "complex"

    Scenario: Dict with string keys is accepted
        When I define a model with a field of type "dict[str, int]"
        Then the model is created successfully

    Scenario: Dict with non-string keys is rejected
        When I define a model with a field of type "dict[int, str]"
        Then a TypeError is raised with message containing "dict keys must be str"

    Scenario: Set of valid type is accepted
        When I define a model with a field of type "set[int]"
        Then the model is created successfully

    Scenario: Tuple of valid types is accepted
        When I define a model with a field of type "tuple[str, int]"
        Then the model is created successfully

    Scenario: Nested container with valid types is accepted
        When I define a model with a field of type "list[dict[str, int]]"
        Then the model is created successfully

    Scenario: Nested container with invalid inner type is rejected
        When I define a model with a field of type "list[dict[str, complex]]"
        Then a TypeError is raised with message containing "complex"

    Scenario: Map subclass is accepted
        When I define a model with a field of type "Map"
        Then the model is created successfully

    Scenario: Dataclass is accepted
        When I define a model with a field of type "dataclass"
        Then the model is created successfully

    Scenario: TypedDict is accepted
        When I define a model with a field of type "TypedDict"
        Then the model is created successfully

    Scenario: Model nested in Model is rejected
        When I define a model with a field of type "Model"
        Then a TypeError is raised with message containing "cannot nest"

    Scenario: Unknown class is rejected
        When I define a model with a field of type "UnknownClass"
        Then a TypeError is raised

    Scenario: User-registered type is accepted
        Given a custom class registered in the type registry
        When I define a model with a field of type "RegisteredCustom"
        Then the model is created successfully

    Scenario: User-registered predicate accepts matching types
        Given a predicate that accepts classes with "__custom__" attribute
        When I define a model with a field of type "CustomClass"
        Then the model is created successfully
