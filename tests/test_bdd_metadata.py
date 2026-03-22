import datetime
from unittest.mock import MagicMock

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from cendry import Cendry, CendryError
from cendry.metadata import _set_metadata, get_metadata
from tests.conftest import SF_DATA, City, make_mock_document

FEATURES = "features"


@scenario(f"{FEATURES}/metadata.feature", "Metadata is populated after reading a document")
def test_metadata_after_get():
    pass


@scenario(f"{FEATURES}/metadata.feature", "Metadata is populated after saving a document")
def test_metadata_after_save():
    pass


@scenario(f"{FEATURES}/metadata.feature", "Metadata is cleared after deleting a document")
def test_metadata_after_delete():
    pass


@scenario(f"{FEATURES}/metadata.feature", "Update with if_unchanged passes precondition")
def test_if_unchanged():
    pass


@scenario(f"{FEATURES}/metadata.feature", "Untracked instance with if_unchanged raises error")
def test_if_unchanged_no_meta():
    pass


@given(
    'a City document "SF" with update_time in Firestore',
    target_fixture="ctx_and_instance",
)
def city_with_update_time():
    client = MagicMock()
    doc = make_mock_document("SF", SF_DATA)
    doc.update_time = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
    doc.create_time = datetime.datetime(2025, 6, 1, tzinfo=datetime.UTC)
    client.collection.return_value.document.return_value.get.return_value = doc
    return Cendry(client=client), None, client


@given(
    parsers.parse('a City instance with id "{doc_id}"'),
    target_fixture="ctx_and_instance",
)
def city_instance(doc_id: str):
    client = MagicMock()
    write_result = MagicMock()
    write_result.update_time = datetime.datetime(2026, 3, 22, tzinfo=datetime.UTC)
    client.collection.return_value.document.return_value.set.return_value = write_result
    instance = City(**SF_DATA, id=doc_id)
    return Cendry(client=client), instance, client


@given(
    parsers.parse('a City instance with id "{doc_id}" and metadata'),
    target_fixture="ctx_and_instance",
)
def city_with_metadata(doc_id: str):
    client = MagicMock()
    write_result = MagicMock()
    write_result.update_time = datetime.datetime(2026, 3, 22, tzinfo=datetime.UTC)
    client.collection.return_value.document.return_value.update.return_value = write_result
    instance = City(**SF_DATA, id=doc_id)
    _set_metadata(
        instance,
        update_time=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
    )
    return Cendry(client=client), instance, client


@given(
    parsers.parse('a City instance with id "{doc_id}" without metadata'),
    target_fixture="ctx_and_instance",
)
def city_without_metadata(doc_id: str):
    client = MagicMock()
    instance = City(**SF_DATA, id=doc_id)
    return Cendry(client=client), instance, client


@when("I read it with ctx.get", target_fixture="result")
def read_with_get(ctx_and_instance):
    ctx, _, _ = ctx_and_instance
    return ctx.get(City, "SF")


@when("I save it and Firestore returns a WriteResult", target_fixture="result")
def save_instance(ctx_and_instance):
    ctx, instance, _ = ctx_and_instance
    ctx.save(instance)
    return instance


@when("I delete the instance", target_fixture="result")
def delete_instance(ctx_and_instance):
    ctx, instance, _ = ctx_and_instance
    ctx.delete(instance)
    return instance


@when("I update with if_unchanged=True", target_fixture="result")
def update_if_unchanged(ctx_and_instance):
    ctx, instance, _ = ctx_and_instance
    try:
        ctx.update(instance, {"population": 900_000}, if_unchanged=True)
        return instance
    except CendryError as e:
        return e


@then("get_metadata returns the update_time")
def check_metadata_update_time(result):
    meta = get_metadata(result)
    assert meta.update_time is not None


@then("get_metadata returns the new update_time")
def check_new_update_time(result):
    meta = get_metadata(result)
    assert meta.update_time == datetime.datetime(2026, 3, 22, tzinfo=datetime.UTC)


@then("get_metadata raises CendryError")
def check_metadata_cleared(result):
    with pytest.raises(CendryError, match="No metadata"):
        get_metadata(result)


@then("the update passes with a LastUpdateOption")
def check_precondition_passed(ctx_and_instance):
    _, _, client = ctx_and_instance
    call_kwargs = client.collection.return_value.document.return_value.update.call_args
    assert call_kwargs.kwargs.get("option") is not None


@then(parsers.parse('a CendryError is raised with message "{message}"'))
def check_cendry_error(result, message: str):
    assert isinstance(result, CendryError)
    assert message in str(result)
