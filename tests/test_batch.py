import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cendry import Cendry, CendryError, Field, Model, field
from cendry.batch import AsyncBatch, Batch
from cendry.types import default_registry
from tests.conftest import SF_DATA, City


class TimestampedEvent(Model, collection="ts_events"):
    title: Field[str]
    updated_at: Field[datetime.datetime | None] = field(auto_now=True)


def make_batch_and_client():
    """Create a mock client and Batch for testing."""
    client = MagicMock()
    fs_batch = MagicMock()

    def get_collection_ref(model_class, parent=None):
        if parent is not None:
            parent_ref = client.collection(parent.__collection__).document(parent.id)
            return parent_ref.collection(model_class.__collection__)
        return client.collection(model_class.__collection__)

    return Batch(fs_batch, get_collection_ref, default_registry), fs_batch, client


# --- Batch.save ---


def test_batch_save_explicit_id():
    batch, fs_batch, _client = make_batch_and_client()
    city = City(**SF_DATA, id="SF")

    batch.save(city)

    fs_batch.set.assert_called_once()


def test_batch_save_auto_id():
    batch, fs_batch, client = make_batch_and_client()
    city = City(**SF_DATA)  # id=None

    doc_ref = client.collection.return_value.document.return_value
    doc_ref.id = "auto-123"

    batch.save(city)

    assert city.id == "auto-123"
    fs_batch.set.assert_called_once()


def test_batch_save_validates_required_fields():
    batch, _fs_batch, _client = make_batch_and_client()
    city = City(
        name=None,
        state="CA",
        country="USA",
        capital=False,
        population=870_000,
        regions=[],
    )

    with pytest.raises(CendryError, match="Required fields are None"):
        batch.save(city)


# --- Batch.create ---


def test_batch_create():
    batch, fs_batch, _client = make_batch_and_client()
    city = City(**SF_DATA, id="SF")

    batch.create(city)

    fs_batch.create.assert_called_once()


def test_batch_create_auto_id():
    batch, _fs_batch, client = make_batch_and_client()
    city = City(**SF_DATA)  # id=None

    doc_ref = client.collection.return_value.document.return_value
    doc_ref.id = "auto-789"

    batch.create(city)

    assert city.id == "auto-789"


# --- Batch.update ---


def test_batch_update_by_instance():
    batch, fs_batch, _client = make_batch_and_client()
    city = City(**SF_DATA, id="SF")

    batch.update(city, {"name": "New Name"})

    fs_batch.update.assert_called_once()


def test_batch_update_by_class_and_id():
    batch, fs_batch, _client = make_batch_and_client()

    batch.update(City, "SF", {"name": "New Name"})

    fs_batch.update.assert_called_once()


def test_batch_update_no_id_raises():
    batch, _fs_batch, _client = make_batch_and_client()
    city = City(**SF_DATA)  # id=None

    with pytest.raises(CendryError, match="Cannot update a model instance with id=None"):
        batch.update(city, {"name": "New"})


# --- Batch.delete ---


def test_batch_delete_by_instance():
    batch, fs_batch, _client = make_batch_and_client()
    city = City(**SF_DATA, id="SF")

    batch.delete(city)

    fs_batch.delete.assert_called_once()


def test_batch_delete_by_class_and_id():
    batch, fs_batch, _client = make_batch_and_client()

    batch.delete(City, "SF")

    fs_batch.delete.assert_called_once()


def test_batch_delete_no_id_raises():
    batch, _fs_batch, _client = make_batch_and_client()
    city = City(**SF_DATA)  # id=None

    with pytest.raises(CendryError, match="Cannot delete a model instance with id=None"):
        batch.delete(city)


# --- Context manager ---


def test_batch_commits_on_exit():
    batch, fs_batch, _ = make_batch_and_client()

    with batch:
        batch.save(City(**SF_DATA, id="SF"))

    fs_batch.commit.assert_called_once()


def test_batch_no_commit_on_exception():
    batch, fs_batch, _ = make_batch_and_client()

    with pytest.raises(ValueError, match="boom"), batch:
        raise ValueError("boom")

    fs_batch.commit.assert_not_called()


# --- AsyncBatch ---


def make_async_batch_and_client():
    client = MagicMock()
    fs_batch = MagicMock()
    fs_batch.commit = AsyncMock()

    def get_collection_ref(model_class, parent=None):
        if parent is not None:
            parent_ref = client.collection(parent.__collection__).document(parent.id)
            return parent_ref.collection(model_class.__collection__)
        return client.collection(model_class.__collection__)

    return AsyncBatch(fs_batch, get_collection_ref, default_registry), fs_batch, client


@pytest.mark.anyio
async def test_async_batch_save():
    batch, fs_batch, _ = make_async_batch_and_client()
    city = City(**SF_DATA, id="SF")

    batch.save(city)

    fs_batch.set.assert_called_once()


@pytest.mark.anyio
async def test_async_batch_commits_on_exit():
    batch, fs_batch, _ = make_async_batch_and_client()

    async with batch:
        batch.save(City(**SF_DATA, id="SF"))

    fs_batch.commit.assert_called_once()


@pytest.mark.anyio
async def test_async_batch_no_commit_on_exception():
    batch, fs_batch, _ = make_async_batch_and_client()

    with pytest.raises(ValueError, match="boom"):
        async with batch:
            raise ValueError("boom")

    fs_batch.commit.assert_not_called()


@pytest.mark.anyio
async def test_async_batch_delete_by_instance():
    batch, fs_batch, _ = make_async_batch_and_client()
    city = City(**SF_DATA, id="SF")

    batch.delete(city)

    fs_batch.delete.assert_called_once()


@pytest.mark.anyio
async def test_async_batch_update_by_instance():
    batch, fs_batch, _ = make_async_batch_and_client()
    city = City(**SF_DATA, id="SF")

    batch.update(city, {"name": "New"})

    fs_batch.update.assert_called_once()


@pytest.mark.anyio
async def test_async_batch_save_auto_id():
    batch, _fs_batch, client = make_async_batch_and_client()
    city = City(**SF_DATA)  # id=None
    doc_ref = client.collection.return_value.document.return_value
    doc_ref.id = "auto-async-123"

    batch.save(city)

    assert city.id == "auto-async-123"


@pytest.mark.anyio
async def test_async_batch_create():
    batch, fs_batch, _ = make_async_batch_and_client()
    city = City(**SF_DATA, id="SF")

    batch.create(city)

    fs_batch.create.assert_called_once()


@pytest.mark.anyio
async def test_async_batch_create_auto_id():
    batch, _fs_batch, client = make_async_batch_and_client()
    city = City(**SF_DATA)  # id=None
    doc_ref = client.collection.return_value.document.return_value
    doc_ref.id = "auto-async-456"

    batch.create(city)

    assert city.id == "auto-async-456"


@pytest.mark.anyio
async def test_async_batch_update_by_class_and_id():
    batch, fs_batch, _ = make_async_batch_and_client()

    batch.update(City, "SF", {"name": "New"})

    fs_batch.update.assert_called_once()


@pytest.mark.anyio
async def test_async_batch_update_no_id_raises():
    batch, _fs_batch, _ = make_async_batch_and_client()
    city = City(**SF_DATA)  # id=None

    with pytest.raises(CendryError, match="Cannot update a model instance with id=None"):
        batch.update(city, {"name": "New"})


@pytest.mark.anyio
async def test_async_batch_delete_no_id_raises():
    batch, _fs_batch, _ = make_async_batch_and_client()
    city = City(**SF_DATA)  # id=None

    with pytest.raises(CendryError, match="Cannot delete a model instance with id=None"):
        batch.delete(city)


@pytest.mark.anyio
async def test_async_batch_delete_by_class_and_id():
    batch, fs_batch, _ = make_async_batch_and_client()

    batch.delete(City, "SF")

    fs_batch.delete.assert_called_once()


# --- auto_timestamps integration ---


@patch("cendry._writes.apply_auto_timestamps")
def test_batch_save_calls_apply_auto_timestamps(mock_apply, mock_firestore_client: MagicMock):
    ctx = Cendry(client=mock_firestore_client)
    with ctx.batch() as batch:
        event = TimestampedEvent(title="test")
        batch.save(event)
    mock_apply.assert_called_once_with(event)


@patch("cendry._writes.apply_auto_timestamps")
def test_batch_create_calls_apply_auto_timestamps(mock_apply, mock_firestore_client: MagicMock):
    ctx = Cendry(client=mock_firestore_client)
    with ctx.batch() as batch:
        event = TimestampedEvent(title="test")
        batch.create(event)
    mock_apply.assert_called_once_with(event)
