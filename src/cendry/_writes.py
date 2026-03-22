"""Shared write-method mixin for Batch and Txn classes."""

from collections.abc import Callable
from typing import Any, TypeVar, overload

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


class WritesMixin:
    """Mixin providing model-aware write methods for batch and transaction wrappers.

    Subclasses must set ``_writer``, ``_get_collection_ref``, and ``_registry``.
    ``_writer`` is the Firestore WriteBatch or Transaction object.
    """

    _writer: Any
    _get_collection_ref: Callable[..., Any]
    _registry: TypeRegistry

    def save(self, instance: T, *, parent: Model | None = None) -> None:
        """Queue a save (upsert). Mutates instance.id if None."""
        validate_required_fields(instance)
        col_ref = self._get_collection_ref(type(instance), parent)
        is_new = instance.id is None
        doc_ref = col_ref.document() if is_new else col_ref.document(instance.id)
        self._writer.set(doc_ref, to_dict(instance, by_alias=True, registry=self._registry))
        if is_new:
            instance.id = doc_ref.id

    def create(self, instance: T, *, parent: Model | None = None) -> None:
        """Queue a create (insert only). Mutates instance.id if None."""
        validate_required_fields(instance)
        col_ref = self._get_collection_ref(type(instance), parent)
        is_new = instance.id is None
        doc_ref = col_ref.document() if is_new else col_ref.document(instance.id)
        self._writer.create(doc_ref, to_dict(instance, by_alias=True, registry=self._registry))
        if is_new:
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
            if not isinstance(field_updates_or_doc_id, str):  # pragma: no cover
                raise CendryError("doc_id must be a string when calling update with a class")
            doc_id = field_updates_or_doc_id
            if field_updates_or_none is None:  # pragma: no cover
                raise CendryError("field_updates is required when calling update with a class")
            field_updates = field_updates_or_none

        resolved = {
            resolve_field_path(model_class, k): serialize_update_value(v, registry=self._registry)
            for k, v in field_updates.items()
        }
        col_ref = self._get_collection_ref(model_class, parent)
        self._writer.update(col_ref.document(doc_id), resolved)

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
            self._writer.delete(col_ref.document(instance_or_class.id))
        else:
            if doc_id is None:  # pragma: no cover
                raise CendryError("doc_id is required when calling delete with a class")
            col_ref = self._get_collection_ref(instance_or_class, parent)
            self._writer.delete(col_ref.document(doc_id))
