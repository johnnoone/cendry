import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from cendry.backends.firestore import FirestoreAsyncBackend, FirestoreBackend


def _mock_client():
    return MagicMock()


def _mock_doc(doc_id, data, exists=True):
    doc = MagicMock()
    doc.id = doc_id
    doc.exists = exists
    doc.to_dict.return_value = data if exists else None
    doc.update_time = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC) if exists else None
    doc.create_time = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC) if exists else None
    return doc


class TestFirestoreBackendRefs:
    def test_get_collection_ref(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        backend.get_collection_ref("cities", None, None)
        client.collection.assert_called_once_with("cities")

    def test_get_collection_ref_with_parent(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        backend.get_collection_ref("neighborhoods", "cities", "SF")
        client.collection.assert_called_once_with("cities")
        client.collection.return_value.document.assert_called_once_with("SF")

    def test_get_doc_ref_with_id(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        col_ref = MagicMock()
        backend.get_doc_ref(col_ref, "SF")
        col_ref.document.assert_called_once_with("SF")

    def test_get_doc_ref_auto_id(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        col_ref = MagicMock()
        backend.get_doc_ref(col_ref, None)
        col_ref.document.assert_called_once_with()

    def test_doc_ref_id(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        doc_ref = MagicMock()
        doc_ref.id = "SF"
        assert backend.doc_ref_id(doc_ref) == "SF"


class TestFirestoreBackendReads:
    def test_get_doc_exists(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        mock_doc = _mock_doc("SF", {"name": "San Francisco"})
        doc_ref = MagicMock()
        doc_ref.get.return_value = mock_doc

        result = backend.get_doc(doc_ref)
        assert result.exists is True
        assert result.doc_id == "SF"
        assert result.data == {"name": "San Francisco"}
        assert result.raw is mock_doc

    def test_get_doc_not_exists(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        mock_doc = _mock_doc("NOPE", {}, exists=False)
        doc_ref = MagicMock()
        doc_ref.get.return_value = mock_doc

        result = backend.get_doc(doc_ref)
        assert result.exists is False

    def test_get_doc_with_transaction(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        mock_doc = _mock_doc("SF", {"name": "SF"})
        doc_ref = MagicMock()
        doc_ref.get.return_value = mock_doc
        txn = MagicMock()

        backend.get_doc(doc_ref, transaction=txn)
        doc_ref.get.assert_called_once_with(transaction=txn)

    def test_get_all(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        doc1 = _mock_doc("SF", {"name": "SF"})
        doc2 = _mock_doc("LA", {"name": "LA"})
        client.get_all.return_value = [doc1, doc2]

        results = list(backend.get_all([MagicMock(), MagicMock()]))
        assert len(results) == 2
        assert results[0].doc_id == "SF"
        assert results[1].doc_id == "LA"


class TestFirestoreBackendWrites:
    def test_set_doc(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        doc_ref = MagicMock()
        mock_write = MagicMock()
        mock_write.update_time = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)
        doc_ref.set.return_value = mock_write

        result = backend.set_doc(doc_ref, {"name": "SF"})
        doc_ref.set.assert_called_once_with({"name": "SF"})
        assert result.update_time is not None

    def test_set_doc_with_writer(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        doc_ref = MagicMock()
        writer = MagicMock()

        backend.set_doc(doc_ref, {"name": "SF"}, writer=writer)
        writer.set.assert_called_once_with(doc_ref, {"name": "SF"})

    def test_create_doc(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        doc_ref = MagicMock()
        mock_write = MagicMock()
        mock_write.update_time = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)
        doc_ref.create.return_value = mock_write

        backend.create_doc(doc_ref, {"name": "SF"})
        doc_ref.create.assert_called_once_with({"name": "SF"})

    def test_create_doc_with_writer(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        doc_ref = MagicMock()
        writer = MagicMock()

        result = backend.create_doc(doc_ref, {"name": "SF"}, writer=writer)
        writer.create.assert_called_once_with(doc_ref, {"name": "SF"})
        assert result.update_time is None

    def test_update_doc(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        doc_ref = MagicMock()
        mock_write = MagicMock()
        mock_write.update_time = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)
        doc_ref.update.return_value = mock_write

        backend.update_doc(doc_ref, {"name": "LA"})
        doc_ref.update.assert_called_once_with({"name": "LA"}, option=None)

    def test_update_doc_with_precondition(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        doc_ref = MagicMock()
        mock_write = MagicMock()
        mock_write.update_time = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)
        doc_ref.update.return_value = mock_write
        precond = MagicMock()

        backend.update_doc(doc_ref, {"name": "LA"}, precondition=precond)
        doc_ref.update.assert_called_once_with({"name": "LA"}, option=precond)

    def test_update_doc_with_writer(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        doc_ref = MagicMock()
        writer = MagicMock()

        result = backend.update_doc(doc_ref, {"name": "LA"}, writer=writer)
        writer.update.assert_called_once_with(doc_ref, {"name": "LA"})
        assert result.update_time is None

    def test_delete_doc(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        doc_ref = MagicMock()

        backend.delete_doc(doc_ref)
        doc_ref.delete.assert_called_once_with(option=None)

    def test_delete_doc_with_writer(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        doc_ref = MagicMock()
        writer = MagicMock()

        backend.delete_doc(doc_ref, writer=writer)
        writer.delete.assert_called_once_with(doc_ref)

    def test_make_precondition(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        dt = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)
        result = backend.make_precondition(dt)
        assert result is not None

    def test_close(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        backend.close()
        client.close.assert_called_once()

    def test_new_batch(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        backend.new_batch()
        client.batch.assert_called_once()

    def test_commit_batch(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        batch = MagicMock()
        backend.commit_batch(batch)
        batch.commit.assert_called_once()

    def test_new_transaction(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        backend.new_transaction(max_attempts=5, read_only=False)
        client.transaction.assert_called_once_with(max_attempts=5, read_only=False)


class TestFirestoreBackendExceptionTranslation:
    def test_create_doc_conflict_raises_already_exists(self):
        from google.cloud.exceptions import Conflict

        from cendry import DocumentAlreadyExistsError

        client = _mock_client()
        backend = FirestoreBackend(client=client)
        doc_ref = MagicMock()
        doc_ref.id = "SF"
        doc_ref.create.side_effect = Conflict("exists")

        with pytest.raises(DocumentAlreadyExistsError):
            backend.create_doc(doc_ref, {"name": "SF"})

    def test_update_doc_not_found_raises_doc_not_found(self):
        from google.api_core.exceptions import NotFound

        from cendry import DocumentNotFoundError

        client = _mock_client()
        backend = FirestoreBackend(client=client)
        doc_ref = MagicMock()
        doc_ref.id = "gone"
        doc_ref.update.side_effect = NotFound("gone")

        with pytest.raises(DocumentNotFoundError):
            backend.update_doc(doc_ref, {"name": "LA"})


class TestFirestoreBackendQueries:
    def test_query(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        col_ref = MagicMock()
        result = backend.query(col_ref)
        assert result is col_ref

    def test_query_group(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        backend.query_group("cities")
        client.collection_group.assert_called_once_with("cities")

    def test_apply_filter(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        query = MagicMock()
        backend.apply_filter(query, "state", "==", "CA")
        query.where.assert_called_once()

    def test_apply_order(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        query = MagicMock()
        backend.apply_order(query, "population", "DESCENDING")
        query.order_by.assert_called_once_with("population", direction="DESCENDING")

    def test_apply_limit(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        query = MagicMock()
        backend.apply_limit(query, 10)
        query.limit.assert_called_once_with(10)

    def test_apply_cursor_start_after(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        query = MagicMock()
        cursor = MagicMock()
        backend.apply_cursor(query, "start_after", cursor)
        query.start_after.assert_called_once_with(cursor)

    def test_apply_cursor_start_at(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        query = MagicMock()
        cursor = MagicMock()
        backend.apply_cursor(query, "start_at", cursor)
        query.start_at.assert_called_once_with(cursor)

    def test_apply_cursor_end_before(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        query = MagicMock()
        cursor = MagicMock()
        backend.apply_cursor(query, "end_before", cursor)
        query.end_before.assert_called_once_with(cursor)

    def test_apply_cursor_end_at(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        query = MagicMock()
        cursor = MagicMock()
        backend.apply_cursor(query, "end_at", cursor)
        query.end_at.assert_called_once_with(cursor)

    def test_stream(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        doc1 = _mock_doc("SF", {"name": "SF"})
        doc2 = _mock_doc("LA", {"name": "LA"})
        query = MagicMock()
        query.stream.return_value = [doc1, doc2]

        results = list(backend.stream(query))
        assert len(results) == 2
        assert results[0].doc_id == "SF"

    def test_select_fields(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        query = MagicMock()
        backend.select_fields(query, ["name", "state"])
        query.select.assert_called_once_with(["name", "state"])

    def test_count(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        query = MagicMock()
        agg_result = MagicMock()
        agg_result.value = 42
        query.count.return_value.get.return_value = [[agg_result]]

        assert backend.count(query) == 42

    def test_on_doc_snapshot(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        doc_ref = MagicMock()
        callback = MagicMock()
        backend.on_doc_snapshot(doc_ref, callback)
        doc_ref.on_snapshot.assert_called_once_with(callback)

    def test_on_query_snapshot(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        query = MagicMock()
        callback = MagicMock()
        backend.on_query_snapshot(query, callback)
        query.on_snapshot.assert_called_once_with(callback)

    def test_apply_composite_and(self):
        from cendry.model import FieldFilterResult

        client = _mock_client()
        backend = FirestoreBackend(client=client)
        query = MagicMock()
        filters = [
            FieldFilterResult("state", "==", "CA"),
            FieldFilterResult("population", ">", 100000),
        ]
        backend.apply_composite(query, "AND", filters)
        query.where.assert_called_once()

    def test_apply_composite_nested(self):
        from cendry import And, Or
        from cendry.model import FieldFilterResult

        client = _mock_client()
        backend = FirestoreBackend(client=client)
        query = MagicMock()
        nested = And(
            Or(FieldFilterResult("state", "==", "CA"), FieldFilterResult("state", "==", "NY")),
            FieldFilterResult("population", ">", 100000),
        )
        backend.apply_composite(query, "AND", list(nested.filters))
        query.where.assert_called_once()

    def test_apply_composite_or(self):
        from cendry.model import FieldFilterResult

        client = _mock_client()
        backend = FirestoreBackend(client=client)
        query = MagicMock()
        filters = [
            FieldFilterResult("state", "==", "CA"),
            FieldFilterResult("state", "==", "NY"),
        ]
        backend.apply_composite(query, "OR", filters)
        query.where.assert_called_once()

    def test_resolve_filter_or(self):
        from cendry import Or
        from cendry.model import FieldFilterResult

        client = _mock_client()
        backend = FirestoreBackend(client=client)
        f = Or(
            FieldFilterResult("state", "==", "CA"),
            FieldFilterResult("state", "==", "NY"),
        )
        result = backend._resolve_filter(f)
        assert result is not None

    def test_resolve_filter_and(self):
        from cendry import And
        from cendry.model import FieldFilterResult

        client = _mock_client()
        backend = FirestoreBackend(client=client)
        f = And(
            FieldFilterResult("state", "==", "CA"),
            FieldFilterResult("population", ">", 100000),
        )
        result = backend._resolve_filter(f)
        assert result is not None

    def test_resolve_filter_passthrough(self):
        client = _mock_client()
        backend = FirestoreBackend(client=client)
        sentinel = object()
        result = backend._resolve_filter(sentinel)
        assert result is sentinel


# --- Async Backend Tests ---


def _async_mock_client():
    return MagicMock()


class TestFirestoreAsyncBackendRefs:
    def test_get_collection_ref(self):
        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        backend.get_collection_ref("cities", None, None)
        client.collection.assert_called_once_with("cities")

    def test_get_collection_ref_with_parent(self):
        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        backend.get_collection_ref("neighborhoods", "cities", "SF")
        client.collection.assert_called_once_with("cities")
        client.collection.return_value.document.assert_called_once_with("SF")

    def test_get_doc_ref_with_id(self):
        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        col_ref = MagicMock()
        backend.get_doc_ref(col_ref, "SF")
        col_ref.document.assert_called_once_with("SF")

    def test_get_doc_ref_auto_id(self):
        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        col_ref = MagicMock()
        backend.get_doc_ref(col_ref, None)
        col_ref.document.assert_called_once_with()

    def test_doc_ref_id(self):
        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        doc_ref = MagicMock()
        doc_ref.id = "SF"
        assert backend.doc_ref_id(doc_ref) == "SF"


class TestFirestoreAsyncBackendReads:
    @pytest.mark.anyio
    async def test_get_doc_exists(self):
        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        mock_doc = _mock_doc("SF", {"name": "San Francisco"})
        doc_ref = MagicMock()
        doc_ref.get = AsyncMock(return_value=mock_doc)

        result = await backend.get_doc(doc_ref)
        assert result.exists is True
        assert result.doc_id == "SF"
        assert result.data == {"name": "San Francisco"}
        assert result.raw is mock_doc

    @pytest.mark.anyio
    async def test_get_doc_not_exists(self):
        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        mock_doc = _mock_doc("NOPE", {}, exists=False)
        doc_ref = MagicMock()
        doc_ref.get = AsyncMock(return_value=mock_doc)

        result = await backend.get_doc(doc_ref)
        assert result.exists is False

    @pytest.mark.anyio
    async def test_get_doc_with_transaction(self):
        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        mock_doc = _mock_doc("SF", {"name": "SF"})
        doc_ref = MagicMock()
        doc_ref.get = AsyncMock(return_value=mock_doc)
        txn = MagicMock()

        await backend.get_doc(doc_ref, transaction=txn)
        doc_ref.get.assert_called_once_with(transaction=txn)

    @pytest.mark.anyio
    async def test_get_all(self):
        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        doc1 = _mock_doc("SF", {"name": "SF"})
        doc2 = _mock_doc("LA", {"name": "LA"})

        async def mock_get_all(*args, **kwargs):
            for doc in [doc1, doc2]:
                yield doc

        client.get_all = mock_get_all

        results = [r async for r in backend.get_all([MagicMock(), MagicMock()])]
        assert len(results) == 2
        assert results[0].doc_id == "SF"
        assert results[1].doc_id == "LA"


class TestFirestoreAsyncBackendWrites:
    @pytest.mark.anyio
    async def test_set_doc(self):
        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        doc_ref = MagicMock()
        mock_write = MagicMock()
        mock_write.update_time = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)
        doc_ref.set = AsyncMock(return_value=mock_write)

        result = await backend.set_doc(doc_ref, {"name": "SF"})
        doc_ref.set.assert_called_once_with({"name": "SF"})
        assert result.update_time is not None

    @pytest.mark.anyio
    async def test_set_doc_with_writer(self):
        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        doc_ref = MagicMock()
        writer = MagicMock()

        result = await backend.set_doc(doc_ref, {"name": "SF"}, writer=writer)
        writer.set.assert_called_once_with(doc_ref, {"name": "SF"})
        assert result.update_time is None

    @pytest.mark.anyio
    async def test_create_doc(self):
        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        doc_ref = MagicMock()
        mock_write = MagicMock()
        mock_write.update_time = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)
        doc_ref.create = AsyncMock(return_value=mock_write)

        result = await backend.create_doc(doc_ref, {"name": "SF"})
        doc_ref.create.assert_called_once_with({"name": "SF"})
        assert result.update_time is not None

    @pytest.mark.anyio
    async def test_create_doc_with_writer(self):
        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        doc_ref = MagicMock()
        writer = MagicMock()

        result = await backend.create_doc(doc_ref, {"name": "SF"}, writer=writer)
        writer.create.assert_called_once_with(doc_ref, {"name": "SF"})
        assert result.update_time is None

    @pytest.mark.anyio
    async def test_create_doc_conflict_raises_already_exists(self):
        from google.cloud.exceptions import Conflict

        from cendry import DocumentAlreadyExistsError

        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        doc_ref = MagicMock()
        doc_ref.id = "SF"
        doc_ref.create = AsyncMock(side_effect=Conflict("exists"))

        with pytest.raises(DocumentAlreadyExistsError):
            await backend.create_doc(doc_ref, {"name": "SF"})

    @pytest.mark.anyio
    async def test_update_doc(self):
        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        doc_ref = MagicMock()
        mock_write = MagicMock()
        mock_write.update_time = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)
        doc_ref.update = AsyncMock(return_value=mock_write)

        result = await backend.update_doc(doc_ref, {"name": "LA"})
        doc_ref.update.assert_called_once_with({"name": "LA"}, option=None)
        assert result.update_time is not None

    @pytest.mark.anyio
    async def test_update_doc_with_writer(self):
        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        doc_ref = MagicMock()
        writer = MagicMock()

        result = await backend.update_doc(doc_ref, {"name": "LA"}, writer=writer)
        writer.update.assert_called_once_with(doc_ref, {"name": "LA"})
        assert result.update_time is None

    @pytest.mark.anyio
    async def test_update_doc_not_found_raises_doc_not_found(self):
        from google.api_core.exceptions import NotFound

        from cendry import DocumentNotFoundError

        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        doc_ref = MagicMock()
        doc_ref.id = "gone"
        doc_ref.update = AsyncMock(side_effect=NotFound("gone"))

        with pytest.raises(DocumentNotFoundError):
            await backend.update_doc(doc_ref, {"name": "LA"})

    @pytest.mark.anyio
    async def test_delete_doc(self):
        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        doc_ref = MagicMock()
        doc_ref.delete = AsyncMock()

        await backend.delete_doc(doc_ref)
        doc_ref.delete.assert_called_once_with(option=None)

    @pytest.mark.anyio
    async def test_delete_doc_with_writer(self):
        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        doc_ref = MagicMock()
        writer = MagicMock()

        await backend.delete_doc(doc_ref, writer=writer)
        writer.delete.assert_called_once_with(doc_ref)

    @pytest.mark.anyio
    async def test_commit_batch(self):
        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        batch = MagicMock()
        batch.commit = AsyncMock()

        await backend.commit_batch(batch)
        batch.commit.assert_called_once()

    @pytest.mark.anyio
    async def test_close(self):
        client = _async_mock_client()
        client.close = AsyncMock()
        backend = FirestoreAsyncBackend(client=client)

        await backend.close()
        client.close.assert_called_once()


class TestFirestoreAsyncBackendQueries:
    def test_query(self):
        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        col_ref = MagicMock()
        assert backend.query(col_ref) is col_ref

    def test_query_group(self):
        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        backend.query_group("cities")
        client.collection_group.assert_called_once_with("cities")

    def test_apply_filter(self):
        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        query = MagicMock()
        backend.apply_filter(query, "state", "==", "CA")
        query.where.assert_called_once()

    def test_apply_order(self):
        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        query = MagicMock()
        backend.apply_order(query, "population", "DESCENDING")
        query.order_by.assert_called_once_with("population", direction="DESCENDING")

    @pytest.mark.anyio
    async def test_stream(self):
        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        doc1 = _mock_doc("SF", {"name": "SF"})
        doc2 = _mock_doc("LA", {"name": "LA"})

        async def mock_stream():
            for doc in [doc1, doc2]:
                yield doc

        query = MagicMock()
        query.stream = mock_stream

        results = [r async for r in backend.stream(query)]
        assert len(results) == 2
        assert results[0].doc_id == "SF"

    @pytest.mark.anyio
    async def test_count(self):
        client = _async_mock_client()
        backend = FirestoreAsyncBackend(client=client)
        query = MagicMock()
        agg_result = MagicMock()
        agg_result.value = 42
        query.count.return_value.get = AsyncMock(return_value=[[agg_result]])

        assert await backend.count(query) == 42
