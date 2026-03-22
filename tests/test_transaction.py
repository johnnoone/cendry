from unittest.mock import AsyncMock, MagicMock

import pytest

from cendry import CendryError, DocumentNotFoundError
from cendry.transaction import AsyncTxn, Txn
from cendry.types import default_registry
from tests.conftest import SF_DATA, City, make_mock_document


def make_txn_and_client():
    """Create a mock client and Txn for testing."""
    client = MagicMock()
    fs_txn = MagicMock()

    def get_collection_ref(model_class, parent=None):
        if parent is not None:
            parent_ref = client.collection(parent.__collection__).document(parent.id)
            return parent_ref.collection(model_class.__collection__)
        return client.collection(model_class.__collection__)

    return Txn(fs_txn, get_collection_ref, default_registry), fs_txn, client


# --- Txn.get / Txn.find ---


def test_txn_get_returns_model():
    txn, fs_txn, client = make_txn_and_client()
    doc = make_mock_document("SF", SF_DATA)
    client.collection.return_value.document.return_value.get.return_value = doc

    city = txn.get(City, "SF")

    assert isinstance(city, City)
    assert city.id == "SF"
    assert city.name == "San Francisco"
    client.collection.return_value.document.return_value.get.assert_called_once_with(
        transaction=fs_txn
    )


def test_txn_get_missing_raises():
    txn, _fs_txn, client = make_txn_and_client()
    doc = make_mock_document("NOPE", {}, exists=False)
    client.collection.return_value.document.return_value.get.return_value = doc

    with pytest.raises(DocumentNotFoundError):
        txn.get(City, "NOPE")


def test_txn_find_returns_model():
    txn, _fs_txn, client = make_txn_and_client()
    doc = make_mock_document("SF", SF_DATA)
    client.collection.return_value.document.return_value.get.return_value = doc

    city = txn.find(City, "SF")
    assert city is not None
    assert city.name == "San Francisco"


def test_txn_find_missing_returns_none():
    txn, _fs_txn, client = make_txn_and_client()
    doc = make_mock_document("NOPE", {}, exists=False)
    client.collection.return_value.document.return_value.get.return_value = doc

    assert txn.find(City, "NOPE") is None


# --- Txn.save ---


def test_txn_save_explicit_id():
    txn, fs_txn, _client = make_txn_and_client()
    city = City(**SF_DATA, id="SF")

    txn.save(city)

    fs_txn.set.assert_called_once()


def test_txn_save_auto_id():
    txn, fs_txn, client = make_txn_and_client()
    city = City(**SF_DATA)
    doc_ref = client.collection.return_value.document.return_value
    doc_ref.id = "auto-123"

    txn.save(city)

    assert city.id == "auto-123"


# --- Txn.create ---


def test_txn_create():
    txn, fs_txn, _client = make_txn_and_client()
    city = City(**SF_DATA, id="SF")

    txn.create(city)

    fs_txn.create.assert_called_once()


# --- Txn.update ---


def test_txn_update_by_instance():
    txn, fs_txn, _client = make_txn_and_client()
    city = City(**SF_DATA, id="SF")

    txn.update(city, {"name": "New"})

    fs_txn.update.assert_called_once()


def test_txn_update_by_class_and_id():
    txn, fs_txn, _client = make_txn_and_client()

    txn.update(City, "SF", {"name": "New"})

    fs_txn.update.assert_called_once()


def test_txn_update_no_id_raises():
    txn, _fs_txn, _client = make_txn_and_client()
    city = City(**SF_DATA)

    with pytest.raises(CendryError, match="Cannot update a model instance with id=None"):
        txn.update(city, {"name": "New"})


# --- Txn.delete ---


def test_txn_delete_by_instance():
    txn, fs_txn, _client = make_txn_and_client()
    city = City(**SF_DATA, id="SF")

    txn.delete(city)

    fs_txn.delete.assert_called_once()


def test_txn_delete_by_class_and_id():
    txn, fs_txn, _client = make_txn_and_client()

    txn.delete(City, "SF")

    fs_txn.delete.assert_called_once()


def test_txn_delete_no_id_raises():
    txn, _fs_txn, _client = make_txn_and_client()
    city = City(**SF_DATA)

    with pytest.raises(CendryError, match="Cannot delete a model instance with id=None"):
        txn.delete(city)


# --- Context manager ---


def test_txn_context_manager_commits():
    txn, fs_txn, _ = make_txn_and_client()

    with txn:
        txn.save(City(**SF_DATA, id="SF"))

    fs_txn._begin.assert_called_once()
    fs_txn._commit.assert_called_once()


def test_txn_context_manager_rollback_on_exception():
    txn, fs_txn, _ = make_txn_and_client()

    with pytest.raises(ValueError, match="boom"):
        with txn:
            raise ValueError("boom")

    fs_txn._begin.assert_called_once()
    fs_txn._rollback.assert_called_once()
    fs_txn._commit.assert_not_called()


# --- AsyncTxn ---


def make_async_txn_and_client():
    client = MagicMock()
    fs_txn = MagicMock()
    fs_txn._begin = AsyncMock()
    fs_txn._commit = AsyncMock()
    fs_txn._rollback = AsyncMock()

    def get_collection_ref(model_class, parent=None):
        if parent is not None:
            parent_ref = client.collection(parent.__collection__).document(parent.id)
            return parent_ref.collection(model_class.__collection__)
        return client.collection(model_class.__collection__)

    return AsyncTxn(fs_txn, get_collection_ref, default_registry), fs_txn, client


@pytest.mark.anyio
async def test_async_txn_get_returns_model():
    txn, fs_txn, client = make_async_txn_and_client()
    doc = make_mock_document("SF", SF_DATA)
    client.collection.return_value.document.return_value.get = AsyncMock(return_value=doc)

    city = await txn.get(City, "SF")

    assert isinstance(city, City)
    assert city.name == "San Francisco"


@pytest.mark.anyio
async def test_async_txn_get_missing_raises():
    txn, _fs_txn, client = make_async_txn_and_client()
    doc = make_mock_document("NOPE", {}, exists=False)
    client.collection.return_value.document.return_value.get = AsyncMock(return_value=doc)

    with pytest.raises(DocumentNotFoundError):
        await txn.get(City, "NOPE")


@pytest.mark.anyio
async def test_async_txn_find_returns_none():
    txn, _fs_txn, client = make_async_txn_and_client()
    doc = make_mock_document("NOPE", {}, exists=False)
    client.collection.return_value.document.return_value.get = AsyncMock(return_value=doc)

    assert await txn.find(City, "NOPE") is None


@pytest.mark.anyio
async def test_async_txn_save():
    txn, fs_txn, _ = make_async_txn_and_client()
    city = City(**SF_DATA, id="SF")

    txn.save(city)

    fs_txn.set.assert_called_once()


@pytest.mark.anyio
async def test_async_txn_create():
    txn, fs_txn, _ = make_async_txn_and_client()
    city = City(**SF_DATA, id="SF")

    txn.create(city)

    fs_txn.create.assert_called_once()


@pytest.mark.anyio
async def test_async_txn_update_by_instance():
    txn, fs_txn, _ = make_async_txn_and_client()
    city = City(**SF_DATA, id="SF")

    txn.update(city, {"name": "New"})

    fs_txn.update.assert_called_once()


@pytest.mark.anyio
async def test_async_txn_update_no_id_raises():
    txn, _fs_txn, _ = make_async_txn_and_client()
    city = City(**SF_DATA)

    with pytest.raises(CendryError, match="Cannot update"):
        txn.update(city, {"name": "New"})


@pytest.mark.anyio
async def test_async_txn_delete_by_instance():
    txn, fs_txn, _ = make_async_txn_and_client()
    city = City(**SF_DATA, id="SF")

    txn.delete(city)

    fs_txn.delete.assert_called_once()


@pytest.mark.anyio
async def test_async_txn_delete_no_id_raises():
    txn, _fs_txn, _ = make_async_txn_and_client()
    city = City(**SF_DATA)

    with pytest.raises(CendryError, match="Cannot delete"):
        txn.delete(city)


@pytest.mark.anyio
async def test_async_txn_context_manager_commits():
    txn, fs_txn, _ = make_async_txn_and_client()

    async with txn:
        txn.save(City(**SF_DATA, id="SF"))

    fs_txn._begin.assert_called_once()
    fs_txn._commit.assert_called_once()


@pytest.mark.anyio
async def test_async_txn_context_manager_rollback_on_exception():
    txn, fs_txn, _ = make_async_txn_and_client()

    with pytest.raises(ValueError, match="boom"):
        async with txn:
            raise ValueError("boom")

    fs_txn._begin.assert_called_once()
    fs_txn._rollback.assert_called_once()
    fs_txn._commit.assert_not_called()
