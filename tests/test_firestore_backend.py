import datetime
from unittest.mock import MagicMock

import pytest

from cendry.backends.firestore import FirestoreBackend


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
