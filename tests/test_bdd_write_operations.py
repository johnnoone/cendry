from unittest.mock import MagicMock

from google.cloud.exceptions import Conflict
from pytest_bdd import given, parsers, scenario, then, when

from cendry import (
    Cendry,
    CendryError,
    DocumentAlreadyExistsError,
    DocumentNotFoundError,
)
from tests.conftest import SF_DATA, City, make_mock_document

FEATURES = "features"


@scenario(f"{FEATURES}/write_operations.feature", "Save a document with an explicit ID")
def test_save_explicit_id():
    pass


@scenario(f"{FEATURES}/write_operations.feature", "Save a document with auto-generated ID")
def test_save_auto_id():
    pass


@scenario(f"{FEATURES}/write_operations.feature", "Create a document successfully")
def test_create_success():
    pass


@scenario(f"{FEATURES}/write_operations.feature", "Create a duplicate document raises error")
def test_create_duplicate():
    pass


@scenario(f"{FEATURES}/write_operations.feature", "Delete a document by instance")
def test_delete_by_instance():
    pass


@scenario(f"{FEATURES}/write_operations.feature", "Delete a document with id None raises error")
def test_delete_no_id():
    pass


@scenario(
    f"{FEATURES}/write_operations.feature",
    "Delete by class and ID with must_exist on missing doc",
)
def test_delete_must_exist():
    pass


@scenario(f"{FEATURES}/write_operations.feature", "Update a document by instance")
def test_bdd_update_by_instance():
    pass


@scenario(f"{FEATURES}/write_operations.feature", "Update a document with id None raises error")
def test_bdd_update_no_id():
    pass


@scenario(f"{FEATURES}/write_operations.feature", "Refresh a document by instance")
def test_bdd_refresh():
    pass


@given(
    parsers.parse('a City instance with id "{doc_id}"'),
    target_fixture="ctx_and_instance",
)
def city_with_id(doc_id: str):
    client = MagicMock()
    doc_ref = client.collection.return_value.document.return_value
    doc_ref.id = doc_id
    instance = City(**SF_DATA, id=doc_id)
    return Cendry(client=client), instance, client


@given("a City instance without an id", target_fixture="ctx_and_instance")
def city_without_id():
    client = MagicMock()
    doc_ref_mock = MagicMock()
    doc_ref_mock.id = "auto-generated-id"
    client.collection.return_value.document.return_value = doc_ref_mock
    instance = City(**SF_DATA)
    return Cendry(client=client), instance, client


@given("the document already exists in Firestore")
def document_exists(ctx_and_instance):
    _, _, client = ctx_and_instance
    client.collection.return_value.document.return_value.create.side_effect = Conflict(
        "already exists"
    )


@given(
    parsers.parse('a Firestore collection without document "{doc_id}"'),
    target_fixture="ctx_and_instance",
)
def collection_without_doc(doc_id: str):
    client = MagicMock()
    doc = make_mock_document(doc_id, {}, exists=False)
    client.collection.return_value.document.return_value.get.return_value = doc
    return Cendry(client=client), None, client


@when("I save the instance", target_fixture="result")
def save_instance(ctx_and_instance):
    ctx, instance, _ = ctx_and_instance
    return ctx.save(instance)


@when("I create the instance", target_fixture="result")
def create_instance(ctx_and_instance):
    ctx, instance, _ = ctx_and_instance
    try:
        return ctx.create(instance)
    except DocumentAlreadyExistsError as e:
        return e


@when("I delete the instance", target_fixture="result")
def delete_instance(ctx_and_instance):
    ctx, instance, _ = ctx_and_instance
    try:
        ctx.delete(instance)
        return None
    except CendryError as e:
        return e


@when(
    parsers.parse('I delete City with id "{doc_id}" and must_exist is true'),
    target_fixture="result",
)
def delete_by_class_must_exist(ctx_and_instance, doc_id: str):
    ctx, _, _ = ctx_and_instance
    try:
        ctx.delete(City, doc_id, must_exist=True)
        return None
    except DocumentNotFoundError as e:
        return e


@then("the document is written to Firestore")
def check_set_called(ctx_and_instance):
    _, _, client = ctx_and_instance
    client.collection.return_value.document.return_value.set.assert_called_once()


@then(parsers.parse('the returned ID is "{expected_id}"'))
def check_returned_id(result, expected_id: str):
    assert result == expected_id


@then("the instance id is set to the generated value")
def check_auto_id_set(ctx_and_instance):
    _, instance, _ = ctx_and_instance
    assert instance.id == "auto-generated-id"


@then("the returned ID matches the generated value")
def check_returned_auto_id(result):
    assert result == "auto-generated-id"


@then("the document is created in Firestore")
def check_create_called(ctx_and_instance):
    _, _, client = ctx_and_instance
    client.collection.return_value.document.return_value.create.assert_called_once()


@then("a DocumentAlreadyExistsError is raised")
def check_already_exists(result):
    assert isinstance(result, DocumentAlreadyExistsError)


@then("the document is deleted from Firestore")
def check_delete_called(ctx_and_instance):
    _, _, client = ctx_and_instance
    client.collection.return_value.document.return_value.delete.assert_called_once()


@then(parsers.parse('a CendryError is raised with message "{message}"'))
def check_cendry_error(result, message: str):
    assert isinstance(result, CendryError)
    assert message in str(result)


@then("a DocumentNotFoundError is raised")
def check_not_found(result):
    assert isinstance(result, DocumentNotFoundError)


@given("the document exists in Firestore with updated data")
def document_with_updated_data(ctx_and_instance):
    _, instance, client = ctx_and_instance
    updated_data = {**SF_DATA, "name": "San Fran", "population": 900_000}
    doc = make_mock_document(instance.id, updated_data)
    client.collection.return_value.document.return_value.get.return_value = doc


@when(
    parsers.parse('I update the instance with {{"name": "{value}"}}'),
    target_fixture="result",
)
def update_instance(ctx_and_instance, value: str):
    ctx, instance, _ = ctx_and_instance
    try:
        ctx.update(instance, {"name": value})
        return None
    except CendryError as e:
        return e


@when("I refresh the instance", target_fixture="result")
def refresh_instance(ctx_and_instance):
    ctx, instance, _ = ctx_and_instance
    ctx.refresh(instance)
    return


@then("the document is updated in Firestore")
def check_update_called(ctx_and_instance):
    _, _, client = ctx_and_instance
    client.collection.return_value.document.return_value.update.assert_called_once()


@then("the instance fields are updated")
def check_refresh_fields(ctx_and_instance):
    _, instance, _ = ctx_and_instance
    assert instance.name == "San Fran"
    assert instance.population == 900_000
