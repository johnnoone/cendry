from __future__ import annotations

from typing import Any, Iterator, TypeVar

from google.cloud.firestore import Client
from google.cloud.firestore_v1.base_query import And as FsAnd
from google.cloud.firestore_v1.base_query import FieldFilter as FsFieldFilter
from google.cloud.firestore_v1.base_query import Or as FsOr

from cendry.exceptions import CendryError, DocumentNotFound
from cendry.filters import And, Filter, Or
from cendry.model import FieldFilterResult, Model

T = TypeVar("T", bound=Model)


class _BaseCendry:
    """Shared logic for sync and async contexts."""

    _client: Any

    def _deserialize(self, model_class: type[T], doc_id: str, data: dict[str, Any]) -> T:
        """Convert a Firestore document dict to a model instance."""
        return model_class(id=doc_id, **data)  # type: ignore[call-arg]

    def _get_collection_ref(self, model_class: type[T], parent: Model | None = None) -> Any:
        """Get a Firestore collection reference, optionally nested under a parent."""
        if parent is not None:
            if parent.id is None:
                raise CendryError("Parent model must have a non-None id")
            parent_ref = self._client.collection(parent.__collection__).document(parent.id)
            return parent_ref.collection(model_class.__collection__)
        return self._client.collection(model_class.__collection__)

    def _build_query(
        self,
        model_class: type[T],
        filters: tuple[Any, ...],
        *,
        order_by: list[Any] | None = None,
        limit: int | None = None,
        start_at: dict[str, Any] | Model | None = None,
        start_after: dict[str, Any] | Model | None = None,
        end_at: dict[str, Any] | Model | None = None,
        end_before: dict[str, Any] | Model | None = None,
        parent: Model | None = None,
        collection_group: bool = False,
    ) -> Any:
        """Build a Firestore query from filters, ordering, and pagination."""
        if collection_group:
            query = self._client.collection_group(model_class.__collection__)
        else:
            query = self._get_collection_ref(model_class, parent)

        for f in filters:
            query = self._apply_filter(query, f)

        if order_by:
            for o in order_by:
                query = query.order_by(o.field, direction=o.direction)

        if limit is not None:
            query = query.limit(limit)

        if start_at is not None:
            query = query.start_at(self._cursor_value(start_at))
        if start_after is not None:
            query = query.start_after(self._cursor_value(start_after))
        if end_at is not None:
            query = query.end_at(self._cursor_value(end_at))
        if end_before is not None:
            query = query.end_before(self._cursor_value(end_before))

        return query

    def _apply_filter(self, query: Any, f: Any) -> Any:
        """Apply a single filter or composite filter to a query."""
        if isinstance(f, FsFieldFilter):
            return query.where(filter=f)
        elif isinstance(f, FieldFilterResult):
            fs_filter = FsFieldFilter(f.field_name, f.op, f.value)
            return query.where(filter=fs_filter)
        elif isinstance(f, And):
            fs_filters = [self._to_firestore_filter(sub) for sub in f.filters]
            return query.where(filter=FsAnd(filters=fs_filters))
        elif isinstance(f, Or):
            fs_filters = [self._to_firestore_filter(sub) for sub in f.filters]
            return query.where(filter=FsOr(filters=fs_filters))
        else:
            raise CendryError(f"Unknown filter type: {type(f)}")

    def _to_firestore_filter(self, f: Any) -> Any:
        """Convert a cendry filter to a Firestore filter."""
        if isinstance(f, FsFieldFilter):
            return f
        elif isinstance(f, FieldFilterResult):
            return FsFieldFilter(f.field_name, f.op, f.value)
        elif isinstance(f, And):
            return FsAnd(filters=[self._to_firestore_filter(sub) for sub in f.filters])
        elif isinstance(f, Or):
            return FsOr(filters=[self._to_firestore_filter(sub) for sub in f.filters])
        else:
            raise CendryError(f"Unknown filter type: {type(f)}")

    def _cursor_value(self, cursor: dict[str, Any] | Model) -> dict[str, Any]:
        """Convert a cursor to a dict for Firestore."""
        if isinstance(cursor, Model):
            import dataclasses

            d: dict[str, Any] = dataclasses.asdict(cursor)  # type: ignore[call-overload]
            d.pop("id", None)
            return d
        return cursor


class Cendry(_BaseCendry):
    """Synchronous Firestore ODM context."""

    def __init__(self, *, client: Client | None = None) -> None:
        self._client = client or Client()

    def get(self, model_class: type[T], document_id: str, *, parent: Model | None = None) -> T:
        """Get a document by ID. Raises DocumentNotFound if it doesn't exist."""
        col_ref = self._get_collection_ref(model_class, parent)
        doc = col_ref.document(document_id).get()
        if not doc.exists:
            raise DocumentNotFound(model_class.__collection__, document_id)
        return self._deserialize(model_class, doc.id, doc.to_dict())

    def find(self, model_class: type[T], document_id: str, *, parent: Model | None = None) -> T | None:
        """Get a document by ID. Returns None if it doesn't exist."""
        col_ref = self._get_collection_ref(model_class, parent)
        doc = col_ref.document(document_id).get()
        if not doc.exists:
            return None
        return self._deserialize(model_class, doc.id, doc.to_dict())

    def select(
        self,
        model_class: type[T],
        *filters: Any,
        order_by: list[Any] | None = None,
        limit: int | None = None,
        start_at: dict[str, Any] | Model | None = None,
        start_after: dict[str, Any] | Model | None = None,
        end_at: dict[str, Any] | Model | None = None,
        end_before: dict[str, Any] | Model | None = None,
        parent: Model | None = None,
    ) -> Iterator[T]:
        """Query documents. Returns a lazy iterator."""
        query = self._build_query(
            model_class, filters, order_by=order_by, limit=limit,
            start_at=start_at, start_after=start_after,
            end_at=end_at, end_before=end_before, parent=parent,
        )
        for doc in query.stream():
            yield self._deserialize(model_class, doc.id, doc.to_dict())

    def select_group(
        self,
        model_class: type[T],
        *filters: Any,
        order_by: list[Any] | None = None,
        limit: int | None = None,
        start_at: dict[str, Any] | Model | None = None,
        start_after: dict[str, Any] | Model | None = None,
        end_at: dict[str, Any] | Model | None = None,
        end_before: dict[str, Any] | Model | None = None,
    ) -> Iterator[T]:
        """Query across all subcollections with the given collection name."""
        query = self._build_query(
            model_class, filters, order_by=order_by, limit=limit,
            start_at=start_at, start_after=start_after,
            end_at=end_at, end_before=end_before,
            collection_group=True,
        )
        for doc in query.stream():
            yield self._deserialize(model_class, doc.id, doc.to_dict())
