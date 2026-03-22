from collections.abc import Callable
from typing import Any, Self, TypeVar, overload

from .exceptions import CendryError, DocumentNotFoundError
from .model import Model
from .serialize import (
    deserialize,
    resolve_field_path,
    serialize_update_value,
    to_dict,
    validate_required_fields,
)
from .types import TypeRegistry

T = TypeVar("T", bound=Model)


class Txn:
    """Synchronous transaction wrapper with model-aware read and write methods.

    Use as a context manager for single-attempt transactions,
    or pass a callback to ``ctx.transaction(fn)`` for auto-retry.
    """

    def __init__(
        self,
        firestore_transaction: Any,
        get_collection_ref: Callable[..., Any],
        registry: TypeRegistry,
    ) -> None:
        self._transaction = firestore_transaction
        self._get_collection_ref = get_collection_ref
        self._registry = registry

    def __enter__(self) -> Self:
        self._transaction._begin()
        return self

    def __exit__(self, exc_type: type[BaseException] | None, *args: object) -> None:
        if exc_type is None:
            self._transaction._commit()
        else:
            self._transaction._rollback()

    # --- Reads ---

    def get(self, model_class: type[T], doc_id: str, *, parent: Model | None = None) -> T:
        """Read a document within the transaction.

        Args:
            model_class: The Model class to deserialize into.
            doc_id: Firestore document ID.
            parent: Parent document for subcollection queries.

        Returns:
            The deserialized model instance.

        Raises:
            DocumentNotFoundError: If the document does not exist.
        """
        col_ref = self._get_collection_ref(model_class, parent)
        doc = col_ref.document(doc_id).get(transaction=self._transaction)
        if not doc.exists:
            raise DocumentNotFoundError(model_class.__collection__, doc_id)
        return deserialize(model_class, doc.id, doc.to_dict(), registry=self._registry)

    def find(self, model_class: type[T], doc_id: str, *, parent: Model | None = None) -> T | None:
        """Read a document within the transaction, returning None if not found."""
        col_ref = self._get_collection_ref(model_class, parent)
        doc = col_ref.document(doc_id).get(transaction=self._transaction)
        if not doc.exists:
            return None
        return deserialize(model_class, doc.id, doc.to_dict(), registry=self._registry)

    # --- Writes ---

    def save(self, instance: T, *, parent: Model | None = None) -> None:
        """Queue a save (upsert). Mutates instance.id if None."""
        validate_required_fields(instance)
        col_ref = self._get_collection_ref(type(instance), parent)
        doc_ref = col_ref.document() if instance.id is None else col_ref.document(instance.id)
        self._transaction.set(doc_ref, to_dict(instance, by_alias=True, registry=self._registry))
        if instance.id is None:
            instance.id = doc_ref.id

    def create(self, instance: T, *, parent: Model | None = None) -> None:
        """Queue a create (insert only). Mutates instance.id if None."""
        validate_required_fields(instance)
        col_ref = self._get_collection_ref(type(instance), parent)
        doc_ref = col_ref.document() if instance.id is None else col_ref.document(instance.id)
        self._transaction.create(
            doc_ref, to_dict(instance, by_alias=True, registry=self._registry)
        )
        if instance.id is None:
            instance.id = doc_ref.id

    @overload
    def update(
        self, instance: Model, field_updates: dict[str, Any], *, parent: Model | None = None
    ) -> None: ...
    @overload
    def update(
        self,
        model_class: type[T],
        doc_id: str,
        field_updates: dict[str, Any],
        *,
        parent: Model | None = None,
    ) -> None: ...

    def update(  # type: ignore[misc]
        self,
        instance_or_class: Model | type[T],
        field_updates_or_doc_id: dict[str, Any] | str,
        field_updates_or_none: dict[str, Any] | None = None,
        *,
        parent: Model | None = None,
    ) -> None:
        """Queue a partial update."""
        if isinstance(instance_or_class, Model):
            if instance_or_class.id is None:
                raise CendryError("Cannot update a model instance with id=None")
            model_class = type(instance_or_class)
            doc_id = instance_or_class.id
            field_updates: dict[str, Any] = field_updates_or_doc_id  # type: ignore[assignment]
        else:
            model_class = instance_or_class
            assert isinstance(field_updates_or_doc_id, str)
            doc_id = field_updates_or_doc_id
            field_updates = field_updates_or_none  # type: ignore[assignment]
            assert field_updates is not None

        resolved = {
            resolve_field_path(model_class, k): serialize_update_value(v, registry=self._registry)
            for k, v in field_updates.items()
        }
        col_ref = self._get_collection_ref(model_class, parent)
        self._transaction.update(col_ref.document(doc_id), resolved)

    @overload
    def delete(self, instance: Model, *, parent: Model | None = None) -> None: ...
    @overload
    def delete(
        self, model_class: type[T], doc_id: str, *, parent: Model | None = None
    ) -> None: ...

    def delete(  # type: ignore[misc]
        self,
        instance_or_class: Model | type[T],
        doc_id: str | None = None,
        *,
        parent: Model | None = None,
    ) -> None:
        """Queue a delete."""
        if isinstance(instance_or_class, Model):
            if instance_or_class.id is None:
                raise CendryError("Cannot delete a model instance with id=None")
            col_ref = self._get_collection_ref(type(instance_or_class), parent)
            self._transaction.delete(col_ref.document(instance_or_class.id))
        else:
            assert doc_id is not None
            col_ref = self._get_collection_ref(instance_or_class, parent)
            self._transaction.delete(col_ref.document(doc_id))


class AsyncTxn:
    """Asynchronous transaction wrapper with model-aware read and write methods.

    Use as an async context manager for single-attempt transactions,
    or pass a callback to ``await ctx.transaction(fn)`` for auto-retry.
    """

    def __init__(
        self,
        firestore_transaction: Any,
        get_collection_ref: Callable[..., Any],
        registry: TypeRegistry,
    ) -> None:
        self._transaction = firestore_transaction
        self._get_collection_ref = get_collection_ref
        self._registry = registry

    async def __aenter__(self) -> Self:
        await self._transaction._begin()
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, *args: object) -> None:
        if exc_type is None:
            await self._transaction._commit()
        else:
            await self._transaction._rollback()

    # --- Reads ---

    async def get(self, model_class: type[T], doc_id: str, *, parent: Model | None = None) -> T:
        """Read a document within the transaction."""
        col_ref = self._get_collection_ref(model_class, parent)
        doc = await col_ref.document(doc_id).get(transaction=self._transaction)
        if not doc.exists:
            raise DocumentNotFoundError(model_class.__collection__, doc_id)
        return deserialize(model_class, doc.id, doc.to_dict(), registry=self._registry)

    async def find(
        self, model_class: type[T], doc_id: str, *, parent: Model | None = None
    ) -> T | None:
        """Read a document within the transaction, returning None if not found."""
        col_ref = self._get_collection_ref(model_class, parent)
        doc = await col_ref.document(doc_id).get(transaction=self._transaction)
        if not doc.exists:
            return None
        return deserialize(model_class, doc.id, doc.to_dict(), registry=self._registry)

    # --- Writes (sync — they queue, don't execute) ---

    def save(self, instance: T, *, parent: Model | None = None) -> None:
        """Queue a save (upsert). Mutates instance.id if None."""
        validate_required_fields(instance)
        col_ref = self._get_collection_ref(type(instance), parent)
        doc_ref = col_ref.document() if instance.id is None else col_ref.document(instance.id)
        self._transaction.set(doc_ref, to_dict(instance, by_alias=True, registry=self._registry))
        if instance.id is None:
            instance.id = doc_ref.id

    def create(self, instance: T, *, parent: Model | None = None) -> None:
        """Queue a create (insert only). Mutates instance.id if None."""
        validate_required_fields(instance)
        col_ref = self._get_collection_ref(type(instance), parent)
        doc_ref = col_ref.document() if instance.id is None else col_ref.document(instance.id)
        self._transaction.create(
            doc_ref, to_dict(instance, by_alias=True, registry=self._registry)
        )
        if instance.id is None:
            instance.id = doc_ref.id

    @overload
    def update(
        self, instance: Model, field_updates: dict[str, Any], *, parent: Model | None = None
    ) -> None: ...
    @overload
    def update(
        self,
        model_class: type[T],
        doc_id: str,
        field_updates: dict[str, Any],
        *,
        parent: Model | None = None,
    ) -> None: ...

    def update(  # type: ignore[misc]
        self,
        instance_or_class: Model | type[T],
        field_updates_or_doc_id: dict[str, Any] | str,
        field_updates_or_none: dict[str, Any] | None = None,
        *,
        parent: Model | None = None,
    ) -> None:
        """Queue a partial update."""
        if isinstance(instance_or_class, Model):
            if instance_or_class.id is None:
                raise CendryError("Cannot update a model instance with id=None")
            model_class = type(instance_or_class)
            doc_id = instance_or_class.id
            field_updates: dict[str, Any] = field_updates_or_doc_id  # type: ignore[assignment]
        else:
            model_class = instance_or_class
            assert isinstance(field_updates_or_doc_id, str)
            doc_id = field_updates_or_doc_id
            field_updates = field_updates_or_none  # type: ignore[assignment]
            assert field_updates is not None

        resolved = {
            resolve_field_path(model_class, k): serialize_update_value(v, registry=self._registry)
            for k, v in field_updates.items()
        }
        col_ref = self._get_collection_ref(model_class, parent)
        self._transaction.update(col_ref.document(doc_id), resolved)

    @overload
    def delete(self, instance: Model, *, parent: Model | None = None) -> None: ...
    @overload
    def delete(
        self, model_class: type[T], doc_id: str, *, parent: Model | None = None
    ) -> None: ...

    def delete(  # type: ignore[misc]
        self,
        instance_or_class: Model | type[T],
        doc_id: str | None = None,
        *,
        parent: Model | None = None,
    ) -> None:
        """Queue a delete."""
        if isinstance(instance_or_class, Model):
            if instance_or_class.id is None:
                raise CendryError("Cannot delete a model instance with id=None")
            col_ref = self._get_collection_ref(type(instance_or_class), parent)
            self._transaction.delete(col_ref.document(instance_or_class.id))
        else:
            assert doc_id is not None
            col_ref = self._get_collection_ref(instance_or_class, parent)
            self._transaction.delete(col_ref.document(doc_id))
