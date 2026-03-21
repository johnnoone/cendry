from unittest.mock import MagicMock

from pytest_bdd import scenario, then, when

from cendry import Cendry
from cendry.query import Query
from tests.conftest import City, make_mock_document

FEATURES = "features"

SF_DATA = {
    "name": "San Francisco",
    "state": "CA",
    "country": "USA",
    "capital": False,
    "population": 870_000,
    "regions": ["west_coast"],
}


def _make_ctx(docs=None):
    client = MagicMock()
    if docs:
        client.collection.return_value.stream.return_value = iter(docs)
        limit_mock = MagicMock()
        limit_mock.stream.return_value = iter(list(docs))
        client.collection.return_value.limit.return_value = limit_mock
    else:
        client.collection.return_value.stream.return_value = iter([])
        limit_mock = MagicMock()
        limit_mock.stream.return_value = iter([])
        client.collection.return_value.limit.return_value = limit_mock
    where_mock = MagicMock()
    where_mock.stream.return_value = iter([])
    client.collection.return_value.where.return_value = where_mock
    order_mock = MagicMock()
    order_mock.stream.return_value = iter([])
    client.collection.return_value.order_by.return_value = order_mock
    return Cendry(client=client)


@scenario(f"{FEATURES}/query_object.feature", "select returns a Query")
def test_select():
    pass


@scenario(f"{FEATURES}/query_object.feature", "filter returns a new Query")
def test_filter():
    pass


@scenario(f"{FEATURES}/query_object.feature", "order_by returns a new Query")
def test_order_by():
    pass


@scenario(f"{FEATURES}/query_object.feature", "limit returns a new Query")
def test_limit():
    pass


@scenario(f"{FEATURES}/query_object.feature", "to_list fetches results")
def test_to_list():
    pass


@scenario(f"{FEATURES}/query_object.feature", "first with results returns instance")
def test_first():
    pass


@scenario(f"{FEATURES}/query_object.feature", "first without results returns None")
def test_first_none():
    pass


@scenario(f"{FEATURES}/query_object.feature", "exists with results returns True")
def test_exists_true():
    pass


@scenario(f"{FEATURES}/query_object.feature", "exists without results returns False")
def test_exists_false():
    pass


@when("I call select on a model", target_fixture="result")
def call_select():
    return _make_ctx().select(City)


@then("I get a Query object")
def check_query(result):
    assert isinstance(result, Query)


@when("I call select and filter", target_fixture="result")
def call_filter():
    ctx = _make_ctx()
    q1 = ctx.select(City)
    q2 = q1.filter(City.state == "CA")
    return q1, q2


@when("I call select and order_by", target_fixture="result")
def call_order_by():
    ctx = _make_ctx()
    q1 = ctx.select(City)
    q2 = q1.order_by(City.population)
    return q1, q2


@when("I call select and limit", target_fixture="result")
def call_limit():
    ctx = _make_ctx()
    q1 = ctx.select(City)
    q2 = q1.limit(10)
    return q1, q2


@then("I get a new Query object")
def check_new_query(result):
    q1, q2 = result
    assert isinstance(q2, Query)
    assert q1 is not q2


@when("I call select and to_list with documents", target_fixture="result")
def call_to_list():
    return _make_ctx([make_mock_document("SF", SF_DATA)]).select(City).to_list()


@then("I get a non-empty list")
def check_non_empty(result):
    assert isinstance(result, list)
    assert len(result) > 0


@when("I call select and first with documents", target_fixture="result")
def call_first_with():
    return _make_ctx([make_mock_document("SF", SF_DATA)]).select(City).first()


@then("I get an instance")
def check_instance(result):
    assert isinstance(result, City)


@when("I call select and first without documents", target_fixture="result")
def call_first_without():
    return _make_ctx().select(City).first()


@then("I get None")
def check_none(result):
    assert result is None


@when("I call select and exists with documents", target_fixture="result")
def call_exists_with():
    return _make_ctx([make_mock_document("SF", SF_DATA)]).select(City).exists()


@then("I get True")
def check_true(result):
    assert result is True


@when("I call select and exists without documents", target_fixture="result")
def call_exists_without():
    return _make_ctx().select(City).exists()


@then("I get False")
def check_false(result):
    assert result is False
