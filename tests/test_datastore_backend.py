import sys
from unittest.mock import MagicMock

import pytest

from cendry import CendryError, DocumentAlreadyExistsError, DocumentNotFoundError

# Mock google.cloud.datastore before importing the backend
_mock_datastore = MagicMock()
_mock_property_filter = MagicMock()
_mock_datastore.query.PropertyFilter = _mock_property_filter


def _make_mock_key(kind: str, id_or_name: str | int, parent: MagicMock | None = None):
    key = MagicMock()
    key.kind = kind
    key.id_or_name = id_or_name
    key.parent = parent
    return key


def _make_mock_entity(key: MagicMock, data: dict[str, object]):
    entity = MagicMock()
    entity.key = key
    entity.__iter__ = MagicMock(return_value=iter(data.keys()))
    entity.__getitem__ = MagicMock(side_effect=lambda k: data[k])
    entity.keys = MagicMock(return_value=data.keys())
    entity.values = MagicMock(return_value=data.values())
    entity.items = MagicMock(return_value=data.items())
    return entity


@pytest.fixture(autouse=True)
def _patch_datastore(monkeypatch):
    """Patch google.cloud.datastore in sys.modules so the backend can import it."""
    mock_query_module = MagicMock()
    mock_query_module.PropertyFilter = _mock_property_filter

    monkeypatch.setitem(sys.modules, "google.cloud.datastore", _mock_datastore)
    monkeypatch.setitem(sys.modules, "google.cloud.datastore.query", mock_query_module)

    if "cendry.backends.datastore" in sys.modules:
        del sys.modules["cendry.backends.datastore"]

    yield

    if "cendry.backends.datastore" in sys.modules:
        del sys.modules["cendry.backends.datastore"]


@pytest.fixture
def backend_classes():
    from cendry.backends.datastore import DatastoreBackend, _CollectionRef, _QueryWrapper

    return DatastoreBackend, _CollectionRef, _QueryWrapper


@pytest.fixture
def backend():
    from cendry.backends.datastore import DatastoreBackend

    return DatastoreBackend(client=MagicMock())


class TestDatastoreBackendRefs:
    def test_get_collection_ref(self, backend):
        ref = backend.get_collection_ref("cities", None, None)
        assert ref.kind == "cities"
        assert ref.ancestor_key is None

    def test_get_collection_ref_with_parent(self, backend):
        ref = backend.get_collection_ref("neighborhoods", "cities", "SF")
        assert ref.kind == "neighborhoods"
        backend._client.key.assert_called_once_with("cities", "SF")
        assert ref.ancestor_key is not None

    def test_get_doc_ref_with_id(self, backend):
        from cendry.backends.datastore import _CollectionRef

        col_ref = _CollectionRef(kind="cities", ancestor_key=None)
        backend.get_doc_ref(col_ref, "SF")
        backend._client.key.assert_called_once_with("cities", "SF")

    def test_get_doc_ref_with_id_and_parent(self, backend):
        from cendry.backends.datastore import _CollectionRef

        ancestor = MagicMock()
        col_ref = _CollectionRef(kind="neighborhoods", ancestor_key=ancestor)
        backend.get_doc_ref(col_ref, "mission")
        backend._client.key.assert_called_once_with("neighborhoods", "mission", parent=ancestor)

    def test_get_doc_ref_auto_id(self, backend):
        from cendry.backends.datastore import _CollectionRef

        auto_key = _make_mock_key("cities", 12345)
        backend._client.allocate_ids.return_value = [auto_key]
        col_ref = _CollectionRef(kind="cities", ancestor_key=None)
        result = backend.get_doc_ref(col_ref, None)
        backend._client.allocate_ids.assert_called_once()
        assert result is auto_key

    def test_doc_ref_id_string(self, backend):
        doc_ref = _make_mock_key("cities", "SF")
        assert backend.doc_ref_id(doc_ref) == "SF"

    def test_doc_ref_id_int_coercion(self, backend):
        doc_ref = _make_mock_key("cities", 12345)
        assert backend.doc_ref_id(doc_ref) == "12345"


class TestDatastoreBackendReads:
    def test_get_doc_exists(self, backend):
        key = _make_mock_key("cities", "SF")
        entity = _make_mock_entity(key, {"name": "San Francisco"})
        backend._client.get.return_value = entity

        result = backend.get_doc(key)
        assert result.exists is True
        assert result.doc_id == "SF"
        assert result.data == {"name": "San Francisco"}
        assert result.update_time is None
        assert result.create_time is None
        assert result.raw is entity

    def test_get_doc_not_exists(self, backend):
        key = _make_mock_key("cities", "NOPE")
        backend._client.get.return_value = None

        result = backend.get_doc(key)
        assert result.exists is False
        assert result.doc_id == "NOPE"
        assert result.data is None
        assert result.raw is None

    def test_get_doc_with_transaction(self, backend):
        key = _make_mock_key("cities", "SF")
        entity = _make_mock_entity(key, {"name": "SF"})
        backend._client.get.return_value = entity
        txn = MagicMock()

        backend.get_doc(key, transaction=txn)
        backend._client.get.assert_called_once_with(key, transaction=txn)

    def test_get_all(self, backend):
        key1 = _make_mock_key("cities", "SF")
        key2 = _make_mock_key("cities", "LA")
        entity1 = _make_mock_entity(key1, {"name": "SF"})
        entity2 = _make_mock_entity(key2, {"name": "LA"})
        backend._client.get_multi.return_value = [entity1, entity2]

        results = list(backend.get_all([key1, key2]))
        assert len(results) == 2
        assert results[0].exists is True
        assert results[0].doc_id == "SF"
        assert results[1].exists is True
        assert results[1].doc_id == "LA"

    def test_get_all_with_missing(self, backend):
        key1 = _make_mock_key("cities", "SF")
        key2 = _make_mock_key("cities", "NOPE")
        entity1 = _make_mock_entity(key1, {"name": "SF"})
        backend._client.get_multi.return_value = [entity1]

        results = list(backend.get_all([key1, key2]))
        assert len(results) == 2
        assert results[0].exists is True
        assert results[1].exists is False
        assert results[1].doc_id == "NOPE"

    def test_get_all_with_transaction(self, backend):
        key1 = _make_mock_key("cities", "SF")
        entity1 = _make_mock_entity(key1, {"name": "SF"})
        backend._client.get_multi.return_value = [entity1]
        txn = MagicMock()

        list(backend.get_all([key1], transaction=txn))
        backend._client.get_multi.assert_called_once_with([key1], transaction=txn)


class TestDatastoreBackendWrites:
    def test_set_doc(self, backend):
        key = _make_mock_key("cities", "SF")
        result = backend.set_doc(key, {"name": "SF"})
        backend._client.put.assert_called_once()
        assert result.update_time is None

    def test_set_doc_with_writer(self, backend):
        writer = MagicMock()
        key = _make_mock_key("cities", "SF")
        result = backend.set_doc(key, {"name": "SF"}, writer=writer)
        writer.put.assert_called_once()
        backend._client.put.assert_not_called()
        assert result.update_time is None

    def test_create_doc_success(self, backend):
        backend._client.get.return_value = None
        key = _make_mock_key("cities", "SF")
        result = backend.create_doc(key, {"name": "SF"})
        backend._client.put.assert_called_once()
        assert result.update_time is None

    def test_create_doc_conflict(self, backend):
        key = _make_mock_key("cities", "SF")
        existing = _make_mock_entity(key, {"name": "SF"})
        backend._client.get.return_value = existing

        with pytest.raises(DocumentAlreadyExistsError):
            backend.create_doc(key, {"name": "SF"})

    def test_create_doc_with_writer(self, backend):
        backend._client.get.return_value = None
        writer = MagicMock()
        key = _make_mock_key("cities", "SF")
        result = backend.create_doc(key, {"name": "SF"}, writer=writer)
        writer.put.assert_called_once()
        backend._client.put.assert_not_called()
        assert result.update_time is None

    def test_update_doc_success(self, backend):
        key = _make_mock_key("cities", "SF")
        entity = _make_mock_entity(key, {"name": "SF"})
        backend._client.get.return_value = entity

        result = backend.update_doc(key, {"name": "San Francisco"})
        entity.update.assert_called_once_with({"name": "San Francisco"})
        backend._client.put.assert_called_once_with(entity)
        assert result.update_time is None

    def test_update_doc_not_found(self, backend):
        key = _make_mock_key("cities", "gone")
        backend._client.get.return_value = None

        with pytest.raises(DocumentNotFoundError):
            backend.update_doc(key, {"name": "LA"})

    def test_update_doc_with_writer(self, backend):
        writer = MagicMock()
        key = _make_mock_key("cities", "SF")
        entity = _make_mock_entity(key, {"name": "SF"})
        backend._client.get.return_value = entity

        result = backend.update_doc(key, {"name": "LA"}, writer=writer)
        writer.put.assert_called_once_with(entity)
        backend._client.put.assert_not_called()
        assert result.update_time is None

    def test_update_doc_ignores_precondition(self, backend):
        key = _make_mock_key("cities", "SF")
        entity = _make_mock_entity(key, {"name": "SF"})
        backend._client.get.return_value = entity

        result = backend.update_doc(key, {"name": "LA"}, precondition=MagicMock())
        assert result.update_time is None

    def test_delete_doc(self, backend):
        key = _make_mock_key("cities", "SF")
        backend.delete_doc(key)
        backend._client.delete.assert_called_once_with(key)

    def test_delete_doc_with_writer(self, backend):
        writer = MagicMock()
        key = _make_mock_key("cities", "SF")
        backend.delete_doc(key, writer=writer)
        writer.delete.assert_called_once_with(key)
        backend._client.delete.assert_not_called()

    def test_delete_doc_ignores_precondition(self, backend):
        key = _make_mock_key("cities", "SF")
        backend.delete_doc(key, precondition=MagicMock())
        backend._client.delete.assert_called_once_with(key)


class TestDatastoreBackendQueries:
    def test_query_creation(self, backend):
        from cendry.backends.datastore import _CollectionRef, _QueryWrapper

        col_ref = _CollectionRef(kind="cities", ancestor_key=None)
        result = backend.query(col_ref)
        assert isinstance(result, _QueryWrapper)
        backend._client.query.assert_called_once_with(kind="cities", ancestor=None)

    def test_query_with_ancestor(self, backend):
        from cendry.backends.datastore import _CollectionRef

        ancestor = MagicMock()
        col_ref = _CollectionRef(kind="neighborhoods", ancestor_key=ancestor)
        backend.query(col_ref)
        backend._client.query.assert_called_once_with(kind="neighborhoods", ancestor=ancestor)

    def test_apply_filter(self, backend):
        from cendry.backends.datastore import _QueryWrapper

        inner_query = MagicMock()
        wrapper = _QueryWrapper(inner_query)
        result = backend.apply_filter(wrapper, "state", "==", "CA")
        inner_query.add_filter.assert_called_once()
        assert result is wrapper

    def test_apply_order_ascending(self, backend):
        from cendry.backends.datastore import _QueryWrapper

        inner_query = MagicMock()
        inner_query.order = []
        wrapper = _QueryWrapper(inner_query)
        result = backend.apply_order(wrapper, "name", "ASCENDING")
        assert inner_query.order == ["name"]
        assert result is wrapper

    def test_apply_order_descending(self, backend):
        from cendry.backends.datastore import _QueryWrapper

        inner_query = MagicMock()
        inner_query.order = []
        wrapper = _QueryWrapper(inner_query)
        result = backend.apply_order(wrapper, "population", "DESCENDING")
        assert inner_query.order == ["-population"]
        assert result is wrapper

    def test_apply_limit(self, backend):
        from cendry.backends.datastore import _QueryWrapper

        inner_query = MagicMock()
        wrapper = _QueryWrapper(inner_query)
        result = backend.apply_limit(wrapper, 10)
        assert wrapper._limit == 10
        assert result is wrapper

    def test_apply_cursor_start_at(self, backend):
        from cendry.backends.datastore import _QueryWrapper

        inner_query = MagicMock()
        wrapper = _QueryWrapper(inner_query)
        cursor = MagicMock()
        result = backend.apply_cursor(wrapper, "start_at", cursor)
        assert wrapper._start_cursor is cursor
        assert result is wrapper

    def test_apply_cursor_start_after(self, backend):
        from cendry.backends.datastore import _QueryWrapper

        inner_query = MagicMock()
        wrapper = _QueryWrapper(inner_query)
        cursor = MagicMock()
        backend.apply_cursor(wrapper, "start_after", cursor)
        assert wrapper._start_cursor is cursor

    def test_apply_cursor_end_at(self, backend):
        from cendry.backends.datastore import _QueryWrapper

        inner_query = MagicMock()
        wrapper = _QueryWrapper(inner_query)
        cursor = MagicMock()
        backend.apply_cursor(wrapper, "end_at", cursor)
        assert wrapper._end_cursor is cursor

    def test_apply_cursor_end_before(self, backend):
        from cendry.backends.datastore import _QueryWrapper

        inner_query = MagicMock()
        wrapper = _QueryWrapper(inner_query)
        cursor = MagicMock()
        backend.apply_cursor(wrapper, "end_before", cursor)
        assert wrapper._end_cursor is cursor

    def test_stream(self, backend):
        from cendry.backends.datastore import _QueryWrapper

        key1 = _make_mock_key("cities", "SF")
        key2 = _make_mock_key("cities", "LA")
        entity1 = _make_mock_entity(key1, {"name": "SF"})
        entity2 = _make_mock_entity(key2, {"name": "LA"})

        inner_query = MagicMock()
        inner_query.fetch.return_value = [entity1, entity2]
        wrapper = _QueryWrapper(inner_query)

        results = list(backend.stream(wrapper))
        assert len(results) == 2
        assert results[0].exists is True
        assert results[0].doc_id == "SF"
        assert results[0].data == {"name": "SF"}
        assert results[1].doc_id == "LA"

    def test_stream_with_limit(self, backend):
        from cendry.backends.datastore import _QueryWrapper

        inner_query = MagicMock()
        inner_query.fetch.return_value = []
        wrapper = _QueryWrapper(inner_query)
        wrapper._limit = 5

        list(backend.stream(wrapper))
        inner_query.fetch.assert_called_once_with(limit=5)

    def test_stream_with_cursors(self, backend):
        from cendry.backends.datastore import _QueryWrapper

        inner_query = MagicMock()
        inner_query.fetch.return_value = []
        wrapper = _QueryWrapper(inner_query)
        wrapper._start_cursor = "abc"
        wrapper._end_cursor = "xyz"

        list(backend.stream(wrapper))
        inner_query.fetch.assert_called_once_with(start_cursor="abc", end_cursor="xyz")

    def test_select_fields(self, backend):
        from cendry.backends.datastore import _QueryWrapper

        inner_query = MagicMock()
        wrapper = _QueryWrapper(inner_query)
        result = backend.select_fields(wrapper, ["name", "state"])
        assert inner_query.projection == ["name", "state"]
        assert result is wrapper

    def test_count(self, backend):
        from cendry.backends.datastore import _QueryWrapper

        inner_query = MagicMock()
        wrapper = _QueryWrapper(inner_query)

        agg_result = MagicMock()
        agg_result.value = 42
        agg_query = MagicMock()
        backend._client.aggregation_query.return_value.count.return_value = agg_query
        agg_query.fetch.return_value = [[agg_result]]

        assert backend.count(wrapper) == 42
        backend._client.aggregation_query.assert_called_once_with(inner_query)


class TestDatastoreBackendComposite:
    def test_apply_composite_and(self, backend):
        from cendry.backends.datastore import _QueryWrapper
        from cendry.model import FieldFilterResult

        inner_query = MagicMock()
        wrapper = _QueryWrapper(inner_query)
        filters = [
            FieldFilterResult("state", "==", "CA"),
            FieldFilterResult("population", ">", 100000),
        ]
        result = backend.apply_composite(wrapper, "AND", filters)
        assert inner_query.add_filter.call_count == 2
        assert result is wrapper

    def test_apply_composite_or_raises(self, backend):
        from cendry.backends.datastore import _QueryWrapper
        from cendry.model import FieldFilterResult

        inner_query = MagicMock()
        wrapper = _QueryWrapper(inner_query)
        filters = [
            FieldFilterResult("state", "==", "CA"),
            FieldFilterResult("state", "==", "NY"),
        ]
        with pytest.raises(CendryError, match="OR queries are not supported"):
            backend.apply_composite(wrapper, "OR", filters)

    def test_apply_composite_nested_and(self, backend):
        from cendry import And
        from cendry.backends.datastore import _QueryWrapper
        from cendry.model import FieldFilterResult

        inner_query = MagicMock()
        wrapper = _QueryWrapper(inner_query)
        nested = And(
            FieldFilterResult("state", "==", "CA"),
            FieldFilterResult("population", ">", 100000),
        )
        backend.apply_composite(wrapper, "AND", list(nested.filters))
        assert inner_query.add_filter.call_count == 2

    def test_apply_composite_deeply_nested_and(self, backend):
        from cendry import And
        from cendry.backends.datastore import _QueryWrapper
        from cendry.model import FieldFilterResult

        inner_query = MagicMock()
        wrapper = _QueryWrapper(inner_query)
        nested = And(
            FieldFilterResult("state", "==", "CA"),
            FieldFilterResult("population", ">", 100000),
        )
        backend.apply_composite(
            wrapper,
            "AND",
            [nested, FieldFilterResult("capital", "==", True)],
        )
        assert inner_query.add_filter.call_count == 3

    def test_apply_composite_nested_or_raises(self, backend):
        from cendry import Or
        from cendry.backends.datastore import _QueryWrapper
        from cendry.model import FieldFilterResult

        inner_query = MagicMock()
        wrapper = _QueryWrapper(inner_query)
        nested_or = Or(
            FieldFilterResult("state", "==", "CA"),
            FieldFilterResult("state", "==", "NY"),
        )
        with pytest.raises(CendryError, match="OR queries are not supported"):
            backend.apply_composite(wrapper, "AND", [nested_or])

    def test_apply_composite_passthrough_filter(self, backend):
        from cendry.backends.datastore import _QueryWrapper

        inner_query = MagicMock()
        wrapper = _QueryWrapper(inner_query)
        sentinel = MagicMock()
        backend.apply_composite(wrapper, "AND", [sentinel, sentinel])
        assert inner_query.add_filter.call_count == 2


class TestDatastoreBackendUnsupported:
    def test_query_group_raises(self, backend):
        with pytest.raises(CendryError, match="Collection group queries"):
            backend.query_group("cities")

    def test_on_doc_snapshot_raises(self, backend):
        with pytest.raises(CendryError, match="Real-time listeners"):
            backend.on_doc_snapshot(MagicMock(), MagicMock())

    def test_on_query_snapshot_raises(self, backend):
        with pytest.raises(CendryError, match="Real-time listeners"):
            backend.on_query_snapshot(MagicMock(), MagicMock())

    def test_make_precondition_raises(self, backend):
        import datetime

        with pytest.raises(CendryError, match="Optimistic locking"):
            backend.make_precondition(datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC))


class TestDatastoreBackendBatchAndTransaction:
    def test_new_batch(self, backend):
        backend.new_batch()
        backend._client.batch.assert_called_once()

    def test_commit_batch(self, backend):
        batch = MagicMock()
        backend.commit_batch(batch)
        batch.commit.assert_called_once()

    def test_new_transaction(self, backend):
        backend.new_transaction(max_attempts=5, read_only=False)
        backend._client.transaction.assert_called_once()

    def test_close_is_noop(self, backend):
        backend.close()  # should not raise


class TestDatastoreBackendQueryWrapper:
    def test_wrapper_fetch_no_params(self):
        from cendry.backends.datastore import _QueryWrapper

        inner_query = MagicMock()
        wrapper = _QueryWrapper(inner_query)
        wrapper.fetch()
        inner_query.fetch.assert_called_once_with()

    def test_wrapper_fetch_with_all_params(self):
        from cendry.backends.datastore import _QueryWrapper

        inner_query = MagicMock()
        wrapper = _QueryWrapper(inner_query)
        wrapper._limit = 10
        wrapper._start_cursor = "start"
        wrapper._end_cursor = "end"
        wrapper.fetch()
        inner_query.fetch.assert_called_once_with(limit=10, start_cursor="start", end_cursor="end")

    def test_wrapper_query_property(self):
        from cendry.backends.datastore import _QueryWrapper

        inner_query = MagicMock()
        wrapper = _QueryWrapper(inner_query)
        assert wrapper.query is inner_query

    def test_wrapper_order_property(self):
        from cendry.backends.datastore import _QueryWrapper

        inner_query = MagicMock()
        inner_query.order = ["name"]
        wrapper = _QueryWrapper(inner_query)
        assert wrapper.order == ["name"]
        wrapper.order = ["-name"]
        assert inner_query.order == ["-name"]

    def test_wrapper_projection_property(self):
        from cendry.backends.datastore import _QueryWrapper

        inner_query = MagicMock()
        inner_query.projection = []
        wrapper = _QueryWrapper(inner_query)
        wrapper.projection = ["name", "state"]
        assert inner_query.projection == ["name", "state"]

    def test_wrapper_projection_getter(self):
        from cendry.backends.datastore import _QueryWrapper

        inner_query = MagicMock()
        inner_query.projection = ["name"]
        wrapper = _QueryWrapper(inner_query)
        assert wrapper.projection == ["name"]

    def test_wrapper_add_filter(self):
        from cendry.backends.datastore import _QueryWrapper

        inner_query = MagicMock()
        wrapper = _QueryWrapper(inner_query)
        sentinel = MagicMock()
        wrapper.add_filter(filter=sentinel)
        inner_query.add_filter.assert_called_once_with(filter=sentinel)

    def test_wrapper_stream(self):
        from cendry.backends.datastore import _EntitySnapshot, _QueryWrapper

        key = _make_mock_key("cities", "SF")
        entity = _make_mock_entity(key, {"name": "SF"})

        inner_query = MagicMock()
        inner_query.fetch.return_value = [entity]
        wrapper = _QueryWrapper(inner_query)

        results = list(wrapper.stream())
        assert len(results) == 1
        assert isinstance(results[0], _EntitySnapshot)
        assert results[0].id == "SF"
        assert results[0].exists is True
        assert results[0].update_time is None
        assert results[0].create_time is None
        assert results[0].to_dict() == {"name": "SF"}


class TestDatastoreBackendEndToEnd:
    def test_cendry_with_datastore_backend_get(self, backend):
        from cendry import Cendry

        key = _make_mock_key("cities", "SF")
        entity = _make_mock_entity(
            key,
            {
                "name": "San Francisco",
                "state": "CA",
                "country": "USA",
                "capital": False,
                "population": 870000,
                "regions": ["west_coast"],
            },
        )
        backend._client.get.return_value = entity
        backend._client.key.return_value = key

        from tests.conftest import City

        db = Cendry(backend=backend)
        city = db.get(City, "SF")
        assert city.name == "San Francisco"

    def test_cendry_with_datastore_backend_save(self, backend):
        from cendry import Cendry

        key = _make_mock_key("cities", "SF")
        backend._client.key.return_value = key

        from tests.conftest import City

        city = City(
            name="San Francisco",
            state="CA",
            country="USA",
            capital=False,
            population=870000,
            regions=["west_coast"],
        )
        db = Cendry(backend=backend)
        db.save(city)
        backend._client.put.assert_called_once()

    def test_cendry_with_datastore_backend_select(self, backend):
        from cendry import Cendry

        inner_query = MagicMock()
        backend._client.query.return_value = inner_query

        key = _make_mock_key("cities", "SF")
        entity = _make_mock_entity(
            key,
            {
                "name": "San Francisco",
                "state": "CA",
                "country": "USA",
                "capital": False,
                "population": 870000,
                "regions": ["west_coast"],
            },
        )
        inner_query.fetch.return_value = [entity]
        inner_query.order = []

        from tests.conftest import City

        db = Cendry(backend=backend)
        results = list(db.select(City))
        assert len(results) == 1
        assert results[0].name == "San Francisco"

    def test_datastore_backend_is_sync_only(self, backend):
        """DatastoreBackend is sync-only -- it has no async methods."""
        import inspect

        assert not inspect.iscoroutinefunction(backend.get_doc)
        assert not inspect.iscoroutinefunction(backend.set_doc)
        assert not inspect.iscoroutinefunction(backend.stream)


class TestCollectionRef:
    def test_collection_ref_fields(self):
        from cendry.backends.datastore import _CollectionRef

        ref = _CollectionRef(kind="cities", ancestor_key=None)
        assert ref.kind == "cities"
        assert ref.ancestor_key is None

    def test_collection_ref_with_ancestor(self):
        from cendry.backends.datastore import _CollectionRef

        ancestor = MagicMock()
        ref = _CollectionRef(kind="neighborhoods", ancestor_key=ancestor)
        assert ref.kind == "neighborhoods"
        assert ref.ancestor_key is ancestor
