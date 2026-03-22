from collections.abc import Callable
from typing import Any, Self

from ._writes import WritesMixin
from .types import TypeRegistry


class Batch(WritesMixin):
    """Synchronous batch writer with model-aware methods.

    Use as a context manager — auto-commits on successful exit.
    """

    def __init__(
        self,
        firestore_batch: Any,
        get_collection_ref: Callable[..., Any],
        registry: TypeRegistry,
    ) -> None:
        self._writer = firestore_batch
        self._get_collection_ref = get_collection_ref
        self._registry = registry

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: type[BaseException] | None, *args: object) -> None:
        if exc_type is None:
            self._writer.commit()


class AsyncBatch(WritesMixin):
    """Asynchronous batch writer with model-aware methods.

    Use as an async context manager — auto-commits on successful exit.
    """

    def __init__(
        self,
        firestore_batch: Any,
        get_collection_ref: Callable[..., Any],
        registry: TypeRegistry,
    ) -> None:
        self._writer = firestore_batch
        self._get_collection_ref = get_collection_ref
        self._registry = registry

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, *args: object) -> None:
        if exc_type is None:
            await self._writer.commit()
