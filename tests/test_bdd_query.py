from pytest_bdd import given, parsers, scenario, then

from cendry import Asc, Desc

FEATURES = "features"


@scenario(f"{FEATURES}/query.feature", "Create ascending order")
def test_ascending():
    pass


@scenario(f"{FEATURES}/query.feature", "Create descending order")
def test_descending():
    pass


@given(
    parsers.parse('an Asc directive on field "{field}"'),
    target_fixture="order",
)
def asc_directive(field: str):
    return Asc(field)


@given(
    parsers.parse('a Desc directive on field "{field}"'),
    target_fixture="order",
)
def desc_directive(field: str):
    return Desc(field)


@then(parsers.parse('the direction is "{direction}"'))
def check_direction(order, direction: str):
    assert order.direction == direction
