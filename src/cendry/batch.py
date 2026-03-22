from collections.abc import Callable
from typing import Any, Self, TypeVar, overload

from .exceptions import CendryError
from .model import Model
from .serialize import (
    resolve_field_path,
    serialize_update_value,
    to_dict,
    validate_required_fields,
)
from .types import TypeRegistry

T = TypeVar("T", bound=Model)


class Batch:
    """Synchronous batch writer with model-aware methods.

    Use as a context manager — auto-commits on successful exit.
    """

    def __init__(
        self,
        firestore_batch: Any,
        get_collection_ref: Callable[..., Any],
        registry: TypeRegistry,
    ) -> None:
        self._batch = firestore_batch
        self._get_collection_ref = get_collection_ref
        self._registry = registry

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: type[BaseException] | None, *args: object) -> None:
        if exc_type is None:
            self._batch.commit()

    def save(self, instance: T, *, parent: Model | None = None) -> None:
        """Queue a save (upsert). Mutates instance.id if None."""
        validate_required_fields(instance)
        col_ref = self._get_collection_ref(type(instance), parent)
        doc_ref = col_ref.document() if instance.id is None else col_ref.document(instance.id)
        self._batch.set(doc_ref, to_dict(instance, by_alias=True, registry=self._registry))
        if instance.id is None:
            instance.id = doc_ref.id

    def create(self, instance: T, *, parent: Model | None = None) -> None:
        """Queue a create (insert only). Mutates instance.id if None."""
        validate_required_fields(instance)
        col_ref = self._get_collection_ref(type(instance), parent)
        doc_ref = col_ref.document() if instance.id is None else col_ref.document(instance.id)
        self._batch.create(doc_ref, to_dict(instance, by_alias=True, registry=self._registry))
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
        self._batch.update(col_ref.document(doc_id), resolved)

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
            self._batch.delete(col_ref.document(instance_or_class.id))
        else:
            assert doc_id is not None
            col_ref = self._get_collection_ref(instance_or_class, parent)
            self._batch.delete(col_ref.document(doc_id))


class AsyncBatch:
    """Asynchronous batch writer with model-aware methods.

    Use as an async context manager — auto-commits on successful exit.
    """

    def __init__(
        self,
        firestore_batch: Any,
        get_collection_ref: Callable[..., Any],
        registry: TypeRegistry,
    ) -> None:
        self._batch = firestore_batch
        self._get_collection_ref = get_collection_ref
        self._registry = registry

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, *args: object) -> None:
        if exc_type is None:
            await self._batch.commit()

    def save(self, instance: T, *, parent: Model | None = None) -> None:
        """Queue a save (upsert). Mutates instance.id if None."""
        validate_required_fields(instance)
        col_ref = self._get_collection_ref(type(instance), parent)
        doc_ref = col_ref.document() if instance.id is None else col_ref.document(instance.id)
        self._batch.set(doc_ref, to_dict(instance, by_alias=True, registry=self._registry))
        if instance.id is None:
            instance.id = doc_ref.id

    def create(self, instance: T, *, parent: Model | None = None) -> None:
        """Queue a create (insert only). Mutates instance.id if None."""
        validate_required_fields(instance)
        col_ref = self._get_collection_ref(type(instance), parent)
        doc_ref = col_ref.document() if instance.id is None else col_ref.document(instance.id)
        self._batch.create(doc_ref, to_dict(instance, by_alias=True, registry=self._registry))
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
        self._batch.update(col_ref.document(doc_id), resolved)

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
            self._batch.delete(col_ref.document(instance_or_class.id))
        else:
            assert doc_id is not None
            col_ref = self._get_collection_ref(instance_or_class, parent)
            self._batch.delete(col_ref.document(doc_id))
