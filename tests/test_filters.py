import pytest
from google.cloud.firestore_v1.base_query import FieldFilter as FirestoreFieldFilter

from cendry import And, CendryError, FieldFilter, Or
from cendry.filters import Filter


def test_field_filter_is_firestore_field_filter():
    assert FieldFilter is FirestoreFieldFilter


def test_field_filter_creation():
    f = FieldFilter("state", "==", "CA")
    assert f.field_path == "state"
    assert f.op_string == "=="
    assert f.value == "CA"


def test_and_combines_filters():
    f1 = FieldFilter("state", "==", "CA")
    f2 = FieldFilter("population", ">", 1000000)
    result = And(f1, f2)
    assert isinstance(result, Filter)


def test_or_combines_filters():
    f1 = FieldFilter("state", "==", "CA")
    f2 = FieldFilter("country", "==", "Japan")
    result = Or(f1, f2)
    assert isinstance(result, Filter)


def test_and_nested_in_or():
    f1 = FieldFilter("state", "==", "CA")
    f2 = FieldFilter("country", "==", "Japan")
    f3 = FieldFilter("population", ">", 1000000)
    result = Or(f1, And(f2, f3))
    assert isinstance(result, Filter)


def test_and_requires_at_least_two():
    with pytest.raises(CendryError):
        And(FieldFilter("state", "==", "CA"))


def test_or_requires_at_least_two():
    with pytest.raises(CendryError):
        Or(FieldFilter("state", "==", "CA"))


# --- repr ---


def test_field_filter_result_repr_dunder():
    """Dunder operators use copy-pasteable dunder form."""
    from cendry import Field, Model

    class City(Model, collection="cities_repr_test"):
        state: Field[str]

    result = City.state == "CA"
    assert repr(result) == "City.state == 'CA'"


def test_field_filter_result_repr_method():
    """Non-dunder operators use method form."""
    from cendry import Field, Model

    class City(Model, collection="cities_repr_test2"):
        regions: Field[list[str]]

    result = City.regions.array_contains("west")
    assert repr(result) == "City.regions.array_contains('west')"


def test_field_filter_result_repr_no_owner():
    """Without owner, falls back to raw form."""
    from cendry.model import FieldFilterResult

    f = FieldFilterResult("state", "==", "CA")
    assert "== 'CA'" in repr(f)


def test_and_repr():
    from cendry import Field, Model

    class City(Model, collection="cities_and_repr"):
        state: Field[str]
        pop: Field[int]

    result = (City.state == "CA") & (City.pop > 100)
    assert "And(" in repr(result)
    assert "City.state == 'CA'" in repr(result)


def test_or_repr():
    from cendry import Field, Model

    class City(Model, collection="cities_or_repr"):
        state: Field[str]

    result = (City.state == "CA") | (City.state == "NY")
    assert "Or(" in repr(result)
    assert "City.state == 'CA'" in repr(result)
