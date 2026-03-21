import dataclasses
from typing import Any, Self, TypeVar, overload

from google.cloud.firestore import Client
from google.cloud.firestore_v1.base_query import And as FsAnd
from google.cloud.firestore_v1.base_query import FieldFilter as FsFieldFilter
from google.cloud.firestore_v1.base_query import Or as FsOr

from google.cloud.exceptions import Conflict

from .exceptions import CendryError, DocumentAlreadyExistsError, DocumentNotFoundError
from .filters import And, Or
from .model import FieldFilterResult, Model
from .query import AsyncQuery, Query
from .serialize import deserialize, to_dict
from .types import TypeRegistry, default_registry

T = TypeVar("T", bound=Model)


class _BaseCendry:
    """Shared logic for sync and async contexts."""

    _client: Any
    type_registry: TypeRegistry

    def _get_collection_ref(self, model_class: type[T], parent: Model | None = None) -> Any:
        """Get a Firestore collection reference, optionally nested under a parent."""
        if parent is not None:
            if parent.id is None:
                raise CendryError("Parent model must have a non-None id")
            parent_ref = self._client.collection(parent.__collection__).document(parent.id)
            return parent_ref.collection(model_class.__collection__)
        return self._client.collection(model_class.__collection__)

    def _validate_required_fields(self, instance: Model) -> None:
        """Raise CendryError if any required fields are None."""
        missing = []
        for f in dataclasses.fields(instance):
            if f.name == "id":
                continue
            has_default = (
                f.default is not dataclasses.MISSING
                or f.default_factory is not dataclasses.MISSING
            )
            if not has_default and getattr(instance, f.name) is None:
                missing.append(f.name)
        if missing:
            fields = ", ".join(missing)
            raise CendryError(f"Required fields are None: {fields}")

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
        if isinstance(f, FieldFilterResult):
            return query.where(filter=FsFieldFilter(f.field_name, f.op, f.value))
        if isinstance(f, And):
            fs_filters = [self._to_firestore_filter(sub) for sub in f.filters]
            return query.where(filter=FsAnd(filters=fs_filters))
        if isinstance(f, Or):
            fs_filters = [self._to_firestore_filter(sub) for sub in f.filters]
            return query.where(filter=FsOr(filters=fs_filters))
        raise CendryError(f"Unknown filter type: {type(f)}")

    def _to_firestore_filter(self, f: Any) -> Any:
        """Convert a cendry filter to a Firestore filter."""
        if isinstance(f, FsFieldFilter):
            return f
        if isinstance(f, FieldFilterResult):
            return FsFieldFilter(f.field_name, f.op, f.value)
        if isinstance(f, And):
            return FsAnd(filters=[self._to_firestore_filter(sub) for sub in f.filters])
        if isinstance(f, Or):
            return FsOr(filters=[self._to_firestore_filter(sub) for sub in f.filters])
        raise CendryError(f"Unknown filter type: {type(f)}")  # pragma: no cover

    def _cursor_value(self, cursor: dict[str, Any] | Model) -> dict[str, Any]:
        """Convert a cursor to a dict for Firestore."""
        if isinstance(cursor, Model):
            d: dict[str, Any] = dataclasses.asdict(cursor)
            d.pop("id", None)
            return d
        return cursor


class Cendry(_BaseCendry):
    """Synchronous Firestore ODM context.

    Args:
        client: Optional Firestore Client. Uses default credentials if not provided.
        type_registry: Optional TypeRegistry override. Uses the global default if not provided.
    """

    def __init__(
        self,
        *,
        client: Client | None = None,
        type_registry: TypeRegistry | None = None,
    ) -> None:
        self._client = client or Client()
        self.type_registry = type_registry or default_registry

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self._client.close()

    def get(self, model_class: type[T], document_id: str, *, parent: Model | None = None) -> T:
        """Fetch a single document by ID.

        Args:
            model_class: The Model class to deserialize into.
            document_id: Firestore document ID.
            parent: Parent document for subcollection queries.

        Returns:
            The deserialized model instance.

        Raises:
            DocumentNotFoundError: If the document does not exist.
        """
        col_ref = self._get_collection_ref(model_class, parent)
        doc = col_ref.document(document_id).get()
        if not doc.exists:
            raise DocumentNotFoundError(model_class.__collection__, document_id)
        return deserialize(model_class, doc.id, doc.to_dict())

    def find(
        self, model_class: type[T], document_id: str, *, parent: Model | None = None
    ) -> T | None:
        """Fetch a single document by ID, returning None if not found.

        Args:
            model_class: The Model class to deserialize into.
            document_id: Firestore document ID.
            parent: Parent document for subcollection queries.

        Returns:
            The deserialized model instance, or None.
        """
        col_ref = self._get_collection_ref(model_class, parent)
        doc = col_ref.document(document_id).get()
        if not doc.exists:
            return None
        return deserialize(model_class, doc.id, doc.to_dict())

    def get_many(
        self,
        model_class: type[T],
        document_ids: list[str],
        *,
        parent: Model | None = None,
    ) -> list[T]:
        """Batch fetch multiple documents by ID in a single round trip.

        Args:
            model_class: The Model class to deserialize into.
            document_ids: List of Firestore document IDs.
            parent: Parent document for subcollection queries.

        Returns:
            List of deserialized model instances.

        Raises:
            DocumentNotFoundError: If any documents are missing.
        """
        col_ref = self._get_collection_ref(model_class, parent)
        doc_refs = [col_ref.document(doc_id) for doc_id in document_ids]
        results: list[T] = []
        missing: list[str] = []
        for doc in self._client.get_all(doc_refs):
            if not doc.exists:
                missing.append(doc.id)
            else:
                results.append(deserialize(model_class, doc.id, doc.to_dict()))
        if missing:
            raise DocumentNotFoundError(model_class.__collection__, ", ".join(missing))
        return results

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
    ) -> Query[T]:
        """Query documents. Returns a Query with convenience methods."""
        q = self._build_query(
            model_class,
            filters,
            order_by=order_by,
            limit=limit,
            start_at=start_at,
            start_after=start_after,
            end_at=end_at,
            end_before=end_before,
            parent=parent,
        )
        return Query(q, model_class, self._apply_filter)

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
    ) -> Query[T]:
        """Query across all subcollections with the given collection name."""
        q = self._build_query(
            model_class,
            filters,
            order_by=order_by,
            limit=limit,
            start_at=start_at,
            start_after=start_after,
            end_at=end_at,
            end_before=end_before,
            collection_group=True,
        )
        return Query(q, model_class, self._apply_filter)

    def save(self, instance: T, *, parent: Model | None = None) -> str:
        """Save (upsert) a document. Returns the document ID.

        Args:
            instance: Model instance to save.
            parent: Parent document for subcollection writes.

        Returns:
            The document ID (auto-generated if instance.id was None).
        """
        self._validate_required_fields(instance)
        col_ref = self._get_collection_ref(type(instance), parent)
        if instance.id is None:
            doc_ref = col_ref.document()
        else:
            doc_ref = col_ref.document(instance.id)
        doc_ref.set(to_dict(instance, by_alias=True))
        if instance.id is None:
            instance.id = doc_ref.id
        return doc_ref.id

    def create(self, instance: T, *, parent: Model | None = None) -> str:
        """Create a document. Raises if it already exists. Returns the document ID.

        Args:
            instance: Model instance to create.
            parent: Parent document for subcollection writes.

        Returns:
            The document ID (auto-generated if instance.id was None).

        Raises:
            DocumentAlreadyExistsError: If the document already exists.
        """
        self._validate_required_fields(instance)
        col_ref = self._get_collection_ref(type(instance), parent)
        if instance.id is None:
            doc_ref = col_ref.document()
        else:
            doc_ref = col_ref.document(instance.id)
        try:
            doc_ref.create(to_dict(instance, by_alias=True))
        except Conflict as e:
            raise DocumentAlreadyExistsError(
                type(instance).__collection__, doc_ref.id
            ) from e
        if instance.id is None:
            instance.id = doc_ref.id
        return doc_ref.id

    @overload
    def delete(self, instance: Model, *, parent: Model | None = None) -> None: ...
    @overload
    def delete(
        self,
        model_class: type[T],
        doc_id: str,
        *,
        parent: Model | None = None,
        must_exist: bool = False,
    ) -> None: ...

    def delete(
        self,
        instance_or_class: Model | type[T],
        doc_id: str | None = None,
        *,
        parent: Model | None = None,
        must_exist: bool = False,
    ) -> None:
        """Delete a document by instance or by class + ID.

        Args:
            instance_or_class: A Model instance, or a Model class.
            doc_id: Document ID (required when passing a class).
            parent: Parent document for subcollection deletes.
            must_exist: If True, raise DocumentNotFoundError when the document doesn't exist.
        """
        if isinstance(instance_or_class, Model):
            if instance_or_class.id is None:
                raise CendryError("Cannot delete a model instance with id=None")
            col_ref = self._get_collection_ref(type(instance_or_class), parent)
            col_ref.document(instance_or_class.id).delete()
        else:
            col_ref = self._get_collection_ref(instance_or_class, parent)
            if must_exist:
                doc = col_ref.document(doc_id).get()
                if not doc.exists:
                    raise DocumentNotFoundError(instance_or_class.__collection__, doc_id)
            col_ref.document(doc_id).delete()


class AsyncCendry(_BaseCendry):
    """Asynchronous Firestore ODM context.

    Works with anyio (asyncio + trio).

    Args:
        client: Optional async Firestore Client.
        type_registry: Optional TypeRegistry override.

    Note:
        `select()` and `select_group()` are regular `def` methods — they return
        `AsyncQuery` synchronously. Only `get`, `find`, `get_many` are `async def`.
    """

    def __init__(
        self,
        *,
        client: Any = None,
        type_registry: TypeRegistry | None = None,
    ) -> None:
        if client is None:
            from google.cloud.firestore import AsyncClient

            client = AsyncClient()
        self._client = client
        self.type_registry = type_registry or default_registry

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self._client.close()

    async def get(
        self, model_class: type[T], document_id: str, *, parent: Model | None = None
    ) -> T:
        """Get a document by ID. Raises DocumentNotFoundError if it doesn't exist."""
        col_ref = self._get_collection_ref(model_class, parent)
        doc = await col_ref.document(document_id).get()
        if not doc.exists:
            raise DocumentNotFoundError(model_class.__collection__, document_id)
        return deserialize(model_class, doc.id, doc.to_dict())

    async def find(
        self, model_class: type[T], document_id: str, *, parent: Model | None = None
    ) -> T | None:
        """Get a document by ID. Returns None if it doesn't exist."""
        col_ref = self._get_collection_ref(model_class, parent)
        doc = await col_ref.document(document_id).get()
        if not doc.exists:
            return None
        return deserialize(model_class, doc.id, doc.to_dict())

    async def get_many(
        self,
        model_class: type[T],
        document_ids: list[str],
        *,
        parent: Model | None = None,
    ) -> list[T]:
        """Batch fetch multiple documents by ID in a single round trip.

        Args:
            model_class: The Model class to deserialize into.
            document_ids: List of Firestore document IDs.
            parent: Parent document for subcollection queries.

        Returns:
            List of deserialized model instances.

        Raises:
            DocumentNotFoundError: If any documents are missing.
        """
        col_ref = self._get_collection_ref(model_class, parent)
        doc_refs = [col_ref.document(doc_id) for doc_id in document_ids]
        results: list[T] = []
        missing: list[str] = []
        async for doc in self._client.get_all(doc_refs):
            if not doc.exists:
                missing.append(doc.id)
            else:
                results.append(deserialize(model_class, doc.id, doc.to_dict()))
        if missing:
            raise DocumentNotFoundError(model_class.__collection__, ", ".join(missing))
        return results

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
    ) -> AsyncQuery[T]:
        """Query documents. Returns an AsyncQuery with convenience methods."""
        q = self._build_query(
            model_class,
            filters,
            order_by=order_by,
            limit=limit,
            start_at=start_at,
            start_after=start_after,
            end_at=end_at,
            end_before=end_before,
            parent=parent,
        )
        return AsyncQuery(q, model_class, self._apply_filter)

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
    ) -> AsyncQuery[T]:
        """Query across all subcollections with the given collection name."""
        q = self._build_query(
            model_class,
            filters,
            order_by=order_by,
            limit=limit,
            start_at=start_at,
            start_after=start_after,
            end_at=end_at,
            end_before=end_before,
            collection_group=True,
        )
        return AsyncQuery(q, model_class, self._apply_filter)

    async def save(self, instance: T, *, parent: Model | None = None) -> str:
        """Save (upsert) a document. Returns the document ID."""
        self._validate_required_fields(instance)
        col_ref = self._get_collection_ref(type(instance), parent)
        if instance.id is None:
            doc_ref = col_ref.document()
        else:
            doc_ref = col_ref.document(instance.id)
        await doc_ref.set(to_dict(instance, by_alias=True))
        if instance.id is None:
            instance.id = doc_ref.id
        return doc_ref.id

    async def create(self, instance: T, *, parent: Model | None = None) -> str:
        """Create a document. Raises if it already exists. Returns the document ID."""
        self._validate_required_fields(instance)
        col_ref = self._get_collection_ref(type(instance), parent)
        if instance.id is None:
            doc_ref = col_ref.document()
        else:
            doc_ref = col_ref.document(instance.id)
        try:
            await doc_ref.create(to_dict(instance, by_alias=True))
        except Conflict as e:
            raise DocumentAlreadyExistsError(
                type(instance).__collection__, doc_ref.id
            ) from e
        if instance.id is None:
            instance.id = doc_ref.id
        return doc_ref.id

    @overload
    async def delete(self, instance: Model, *, parent: Model | None = None) -> None: ...
    @overload
    async def delete(
        self,
        model_class: type[T],
        doc_id: str,
        *,
        parent: Model | None = None,
        must_exist: bool = False,
    ) -> None: ...

    async def delete(
        self,
        instance_or_class: Model | type[T],
        doc_id: str | None = None,
        *,
        parent: Model | None = None,
        must_exist: bool = False,
    ) -> None:
        """Delete a document by instance or by class + ID."""
        if isinstance(instance_or_class, Model):
            if instance_or_class.id is None:
                raise CendryError("Cannot delete a model instance with id=None")
            col_ref = self._get_collection_ref(type(instance_or_class), parent)
            await col_ref.document(instance_or_class.id).delete()
        else:
            col_ref = self._get_collection_ref(instance_or_class, parent)
            if must_exist:
                doc = await col_ref.document(doc_id).get()
                if not doc.exists:
                    raise DocumentNotFoundError(instance_or_class.__collection__, doc_id)
            await col_ref.document(doc_id).delete()
