from pytest_bdd import given, parsers, scenario, then, when

from cendry import And, Field, FieldFilter, Model, Or
from cendry.filters import Filter

FEATURES = "features"


@scenario(f"{FEATURES}/filters.feature", "Create a field filter")
def test_create_field_filter():
    pass


@scenario(f"{FEATURES}/filters.feature", "Compose filters with AND")
def test_compose_and():
    pass


@scenario(f"{FEATURES}/filters.feature", "Compose filters with OR")
def test_compose_or():
    pass


@scenario(f"{FEATURES}/filters.feature", "Field descriptor produces a filter")
def test_field_descriptor_filter():
    pass


@given(
    parsers.parse('a FieldFilter with field "{field}", operator "{op}" and value "{value}"'),
    target_fixture="field_filter",
)
def create_field_filter(field: str, op: str, value: str):
    return FieldFilter(field, op, value)


@then("the filter is a valid Firestore FieldFilter")
def check_firestore_filter(field_filter):
    from google.cloud.firestore_v1.base_query import FieldFilter as FsFieldFilter

    assert isinstance(field_filter, FsFieldFilter)


@given("two field filters", target_fixture="two_filters")
def two_filters():
    return FieldFilter("state", "==", "CA"), FieldFilter("population", ">", 1000000)


@when("I combine them with And", target_fixture="composite")
def combine_and(two_filters):
    return And(*two_filters)


@when("I combine them with Or", target_fixture="composite")
def combine_or(two_filters):
    return Or(*two_filters)


@then("the result is a composite filter")
def check_composite(composite):
    assert isinstance(composite, Filter)


@given(
    parsers.parse('a model with a "{field_name}" field'),
    target_fixture="test_model",
)
def model_with_field(field_name: str):
    return type(
        "TestModel",
        (Model,),
        {"__annotations__": {field_name: Field[str]}},
        collection="test",
    )


@when(
    parsers.parse('I call eq("{value}") on the field descriptor'),
    target_fixture="filter_result",
)
def call_eq(test_model, value: str):
    return test_model.state.eq(value)


@then(parsers.parse('the result is a filter with operator "{op}"'))
def check_filter_op(filter_result, op: str):
    assert isinstance(filter_result, Filter)
    assert filter_result.op == op
