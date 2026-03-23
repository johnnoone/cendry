from collections.abc import Callable
from typing import Any, Self, TypeVar

from ._writes import WritesMixin
from .exceptions import DocumentNotFoundError
from .metadata import _set_metadata
from .model import Model
from .serialize import deserialize
from .types import TypeRegistry

T = TypeVar("T", bound=Model)


class Txn(WritesMixin):
    """Synchronous transaction wrapper with model-aware read and write methods.

    Use as a context manager for single-attempt transactions,
    or pass a callback to ``ctx.transaction(fn)`` for auto-retry.
    """

    def __init__(
        self,
        firestore_transaction: Any,
        get_collection_ref: Callable[..., Any],
        registry: TypeRegistry,
        backend: Any = None,
    ) -> None:
        self._transaction = firestore_transaction
        self._writer = firestore_transaction
        self._backend = backend
        self._get_collection_ref = get_collection_ref
        self._registry = registry

    def __enter__(self) -> Self:
        _begin = getattr(self._transaction, "_begin", None) or self._transaction.begin
        _begin()
        return self

    def __exit__(self, exc_type: type[BaseException] | None, *args: object) -> None:
        if exc_type is None:
            _commit = getattr(self._transaction, "_commit", None) or self._transaction.commit
            _commit()
        else:
            _rollback = getattr(self._transaction, "_rollback", None) or self._transaction.rollback
            _rollback()

    def get(self, model_class: type[T], doc_id: str, *, parent: Model | None = None) -> T:
        """Read a document within the transaction.

        Raises:
            DocumentNotFoundError: If the document does not exist.
        """
        col_ref = self._get_collection_ref(model_class, parent)
        if self._backend is not None:  # pragma: no cover
            doc_ref = self._backend.get_doc_ref(col_ref, doc_id)
            doc = self._backend.get_doc(doc_ref, transaction=self._transaction)
            if not doc.exists:
                raise DocumentNotFoundError(model_class.__collection__, doc_id)
            result = deserialize(model_class, doc.doc_id, doc.data, registry=self._registry)
            _set_metadata(result, update_time=doc.update_time, create_time=doc.create_time)
            return result
        doc = col_ref.document(doc_id).get(transaction=self._transaction)
        if not doc.exists:
            raise DocumentNotFoundError(model_class.__collection__, doc_id)
        result = deserialize(model_class, doc.id, doc.to_dict(), registry=self._registry)
        _set_metadata(result, update_time=doc.update_time, create_time=doc.create_time)
        return result

    def find(self, model_class: type[T], doc_id: str, *, parent: Model | None = None) -> T | None:
        """Read a document within the transaction, returning None if not found."""
        col_ref = self._get_collection_ref(model_class, parent)
        if self._backend is not None:  # pragma: no cover
            doc_ref = self._backend.get_doc_ref(col_ref, doc_id)
            doc = self._backend.get_doc(doc_ref, transaction=self._transaction)
            if not doc.exists:
                return None
            result = deserialize(model_class, doc.doc_id, doc.data, registry=self._registry)
            _set_metadata(result, update_time=doc.update_time, create_time=doc.create_time)
            return result
        doc = col_ref.document(doc_id).get(transaction=self._transaction)
        if not doc.exists:
            return None
        result = deserialize(model_class, doc.id, doc.to_dict(), registry=self._registry)
        _set_metadata(result, update_time=doc.update_time, create_time=doc.create_time)
        return result


class AsyncTxn(WritesMixin):
    """Asynchronous transaction wrapper with model-aware read and write methods.

    Use as an async context manager for single-attempt transactions,
    or pass a callback to ``await ctx.transaction(fn)`` for auto-retry.
    Write methods are synchronous — they queue operations, not execute them.
    """

    def __init__(
        self,
        firestore_transaction: Any,
        get_collection_ref: Callable[..., Any],
        registry: TypeRegistry,
        backend: Any = None,
    ) -> None:
        self._transaction = firestore_transaction
        self._writer = firestore_transaction
        self._backend = backend
        self._get_collection_ref = get_collection_ref
        self._registry = registry

    async def __aenter__(self) -> Self:
        _begin = getattr(self._transaction, "_begin", None) or self._transaction.begin
        await _begin()
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, *args: object) -> None:
        if exc_type is None:
            _commit = getattr(self._transaction, "_commit", None) or self._transaction.commit
            await _commit()
        else:
            _rollback = getattr(self._transaction, "_rollback", None) or self._transaction.rollback
            await _rollback()

    async def get(self, model_class: type[T], doc_id: str, *, parent: Model | None = None) -> T:
        """Read a document within the transaction."""
        col_ref = self._get_collection_ref(model_class, parent)
        if self._backend is not None:  # pragma: no cover
            doc_ref = self._backend.get_doc_ref(col_ref, doc_id)
            doc = await self._backend.get_doc(doc_ref, transaction=self._transaction)
            if not doc.exists:
                raise DocumentNotFoundError(model_class.__collection__, doc_id)
            result = deserialize(model_class, doc.doc_id, doc.data, registry=self._registry)
            _set_metadata(result, update_time=doc.update_time, create_time=doc.create_time)
            return result
        doc = await col_ref.document(doc_id).get(transaction=self._transaction)
        if not doc.exists:
            raise DocumentNotFoundError(model_class.__collection__, doc_id)
        result = deserialize(model_class, doc.id, doc.to_dict(), registry=self._registry)
        _set_metadata(result, update_time=doc.update_time, create_time=doc.create_time)
        return result

    async def find(
        self, model_class: type[T], doc_id: str, *, parent: Model | None = None
    ) -> T | None:
        """Read a document within the transaction, returning None if not found."""
        col_ref = self._get_collection_ref(model_class, parent)
        if self._backend is not None:  # pragma: no cover
            doc_ref = self._backend.get_doc_ref(col_ref, doc_id)
            doc = await self._backend.get_doc(doc_ref, transaction=self._transaction)
            if not doc.exists:
                return None
            result = deserialize(model_class, doc.doc_id, doc.data, registry=self._registry)
            _set_metadata(result, update_time=doc.update_time, create_time=doc.create_time)
            return result
        doc = await col_ref.document(doc_id).get(transaction=self._transaction)
        if not doc.exists:
            return None
        result = deserialize(model_class, doc.id, doc.to_dict(), registry=self._registry)
        _set_metadata(result, update_time=doc.update_time, create_time=doc.create_time)
        return result
