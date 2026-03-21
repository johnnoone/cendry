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


def test_field_filter_result_repr():
    from cendry.model import FieldFilterResult

    f = FieldFilterResult("state", "==", "CA")
    assert repr(f) == 'FieldFilter("state", "==", \'CA\')'


def test_field_filter_result_repr_int():
    from cendry.model import FieldFilterResult

    f = FieldFilterResult("population", ">", 1_000_000)
    assert repr(f) == 'FieldFilter("population", ">", 1000000)'


def test_and_repr():
    from cendry.model import FieldFilterResult

    f1 = FieldFilterResult("state", "==", "CA")
    f2 = FieldFilterResult("pop", ">", 100)
    result = And(f1, f2)
    assert "And(" in repr(result)
    assert "FieldFilter(" in repr(result)


def test_or_repr():
    from cendry.model import FieldFilterResult

    f1 = FieldFilterResult("state", "==", "CA")
    f2 = FieldFilterResult("state", "==", "NY")
    result = Or(f1, f2)
    assert "Or(" in repr(result)
    assert "FieldFilter(" in repr(result)
