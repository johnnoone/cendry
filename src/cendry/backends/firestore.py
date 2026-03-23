"""Firestore backend implementation."""

import datetime
from collections.abc import Iterator
from typing import Any, Literal

from google.api_core.exceptions import NotFound
from google.cloud.exceptions import Conflict
from google.cloud.firestore_v1._helpers import LastUpdateOption

from ..backends.types import DocResult, WriteResult
from ..exceptions import DocumentAlreadyExistsError, DocumentNotFoundError


class FirestoreBackend:
    """Sync Firestore backend wrapping google.cloud.firestore.Client."""

    def __init__(self, *, client: Any = None) -> None:
        if client is None:
            from google.cloud.firestore import Client

            client = Client()
        self._client = client

    def get_collection_ref(
        self, collection: str, parent_collection: str | None, parent_id: str | None
    ) -> Any:
        if parent_collection is not None and parent_id is not None:
            return (
                self._client.collection(parent_collection)
                .document(parent_id)
                .collection(collection)
            )
        return self._client.collection(collection)

    def get_doc_ref(self, col_ref: Any, doc_id: str | None) -> Any:
        if doc_id is None:
            return col_ref.document()
        return col_ref.document(doc_id)

    def doc_ref_id(self, doc_ref: Any) -> str:
        return doc_ref.id

    def get_doc(self, doc_ref: Any, *, transaction: Any | None = None) -> DocResult:
        snapshot = doc_ref.get(transaction=transaction)
        return DocResult(
            exists=snapshot.exists,
            doc_id=snapshot.id,
            data=snapshot.to_dict() if snapshot.exists else None,
            update_time=snapshot.update_time if snapshot.exists else None,
            create_time=snapshot.create_time if snapshot.exists else None,
            raw=snapshot,
        )

    def get_all(
        self, doc_refs: list[Any], *, transaction: Any | None = None
    ) -> Iterator[DocResult]:
        for snapshot in self._client.get_all(doc_refs, transaction=transaction):
            yield DocResult(
                exists=snapshot.exists,
                doc_id=snapshot.id,
                data=snapshot.to_dict() if snapshot.exists else None,
                update_time=snapshot.update_time if snapshot.exists else None,
                create_time=snapshot.create_time if snapshot.exists else None,
                raw=snapshot,
            )

    def set_doc(
        self, doc_ref: Any, data: dict[str, Any], *, writer: Any | None = None
    ) -> WriteResult:
        if writer is not None:
            writer.set(doc_ref, data)
            return WriteResult(update_time=None)
        result = doc_ref.set(data)
        return WriteResult(update_time=result.update_time)

    def create_doc(
        self, doc_ref: Any, data: dict[str, Any], *, writer: Any | None = None
    ) -> WriteResult:
        if writer is not None:
            writer.create(doc_ref, data)
            return WriteResult(update_time=None)
        try:
            result = doc_ref.create(data)
        except Conflict:
            raise DocumentAlreadyExistsError("", doc_ref.id) from None
        return WriteResult(update_time=result.update_time)

    def update_doc(
        self,
        doc_ref: Any,
        updates: dict[str, Any],
        *,
        writer: Any | None = None,
        precondition: Any | None = None,
    ) -> WriteResult:
        if writer is not None:
            writer.update(doc_ref, updates)
            return WriteResult(update_time=None)
        try:
            result = doc_ref.update(updates, option=precondition)
        except NotFound:
            raise DocumentNotFoundError("", doc_ref.id) from None
        return WriteResult(update_time=result.update_time)

    def delete_doc(
        self,
        doc_ref: Any,
        *,
        writer: Any | None = None,
        precondition: Any | None = None,
    ) -> None:
        if writer is not None:
            writer.delete(doc_ref)
            return
        doc_ref.delete(option=precondition)

    def query(self, col_ref: Any) -> Any:
        raise NotImplementedError  # pragma: no cover

    def query_group(self, collection: str) -> Any:
        raise NotImplementedError  # pragma: no cover

    def apply_filter(self, query: Any, field: str, op: str, value: Any) -> Any:
        raise NotImplementedError  # pragma: no cover

    def apply_composite(self, query: Any, op: str, filters: list[Any]) -> Any:
        raise NotImplementedError  # pragma: no cover

    def apply_order(self, query: Any, field: str, direction: str) -> Any:
        raise NotImplementedError  # pragma: no cover

    def apply_limit(self, query: Any, n: int) -> Any:
        raise NotImplementedError  # pragma: no cover

    def apply_cursor(
        self,
        query: Any,
        cursor_type: Literal["start_at", "start_after", "end_at", "end_before"],
        value: Any,
    ) -> Any:
        raise NotImplementedError  # pragma: no cover

    def stream(self, query: Any) -> Iterator[DocResult]:
        raise NotImplementedError  # pragma: no cover

    def select_fields(self, query: Any, fields: list[str]) -> Any:
        raise NotImplementedError  # pragma: no cover

    def count(self, query: Any) -> int:
        raise NotImplementedError  # pragma: no cover

    def new_batch(self) -> Any:
        return self._client.batch()

    def new_transaction(self, max_attempts: int, read_only: bool) -> Any:
        return self._client.transaction(max_attempts=max_attempts, read_only=read_only)

    def commit_batch(self, batch: Any) -> None:
        batch.commit()

    def on_doc_snapshot(self, doc_ref: Any, callback: Any) -> Any:
        raise NotImplementedError  # pragma: no cover

    def on_query_snapshot(self, query: Any, callback: Any) -> Any:
        raise NotImplementedError  # pragma: no cover

    def make_precondition(self, update_time: datetime.datetime) -> Any:
        return LastUpdateOption(update_time)

    def close(self) -> None:
        self._client.close()
