from unittest.mock import MagicMock

from pytest_bdd import given, parsers, scenario, then, when

from cendry import Cendry, DocumentNotFound
from tests.conftest import City, make_mock_document

FEATURES = "features"


@scenario(f"{FEATURES}/context.feature", "Get a document by ID")
def test_get_document():
    pass


@scenario(f"{FEATURES}/context.feature", "Get a non-existent document raises error")
def test_get_not_found():
    pass


@scenario(f"{FEATURES}/context.feature", "Find a non-existent document returns None")
def test_find_not_found():
    pass


@given(
    parsers.parse('a Firestore collection "{col}" with a document "{doc_id}"'),
    target_fixture="context_and_id",
)
def collection_with_doc(doc_id: str):
    client = MagicMock()
    doc = make_mock_document(doc_id, {
        "name": "San Francisco", "state": "CA", "country": "USA",
        "capital": False, "population": 870000, "regions": ["west_coast"],
    })
    client.collection.return_value.document.return_value.get.return_value = doc
    return Cendry(client=client), doc_id


@given(
    parsers.parse('a Firestore collection "{col}" without document "{doc_id}"'),
    target_fixture="context_and_id",
)
def collection_without_doc(doc_id: str):
    client = MagicMock()
    doc = make_mock_document(doc_id, {}, exists=False)
    client.collection.return_value.document.return_value.get.return_value = doc
    return Cendry(client=client), doc_id


@when(
    parsers.parse('I call get with model City and id "{doc_id}"'),
    target_fixture="get_result",
)
def call_get(context_and_id, doc_id: str):
    ctx, _ = context_and_id
    try:
        return ctx.get(City, doc_id)
    except DocumentNotFound as e:
        return e


@when(
    parsers.parse('I call find with model City and id "{doc_id}"'),
    target_fixture="find_result",
)
def call_find(context_and_id, doc_id: str):
    ctx, _ = context_and_id
    return ctx.find(City, doc_id)


@then(parsers.parse('I receive a City instance with id "{doc_id}"'))
def check_city(get_result, doc_id: str):
    assert isinstance(get_result, City)
    assert get_result.id == doc_id


@then("a DocumentNotFound error is raised")
def check_not_found(get_result):
    assert isinstance(get_result, DocumentNotFound)


@then("the result is None")
def check_none(find_result):
    assert find_result is None
