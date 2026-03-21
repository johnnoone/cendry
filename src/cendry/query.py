from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any

from .exceptions import CendryError, DocumentNotFoundError
from .model import FieldDescriptor, Model
from .serialize import deserialize


class _Order:
    """Base class for ordering directives."""

    direction: str

    def __init__(self, field: str | FieldDescriptor) -> None:
        if isinstance(field, FieldDescriptor):
            self.field = field.field_name
        else:
            self.field = field


class Asc(_Order):
    """Ascending order."""

    direction = "ASCENDING"


class Desc(_Order):
    """Descending order."""

    direction = "DESCENDING"


class Query[T: Model]:
    """Synchronous query result with convenience methods.

    Immutable — filter() returns a new Query.
    Reusable — each method creates a new stream.
    """

    def __init__(
        self,
        firestore_query: Any,
        model_class: type[T],
        apply_filter: Callable[[Any, Any], Any],
    ) -> None:
        self._query = firestore_query
        self._model_class = model_class
        self._apply_filter = apply_filter

    def __iter__(self) -> Iterator[T]:
        for doc in self._query.stream():
            yield deserialize(self._model_class, doc.id, doc.to_dict())

    def filter(self, *filters: Any) -> "Query[T]":
        """Add filters to the query. Returns a new Query."""
        query = self._query
        for f in filters:
            if isinstance(f, list):
                for sub in f:
                    query = self._apply_filter(query, sub)
            else:
                query = self._apply_filter(query, f)
        return Query(query, self._model_class, self._apply_filter)

    def to_list(self) -> list[T]:
        """Fetch all matching documents."""
        return list(self)

    def first(self) -> T | None:
        """Fetch the first matching document, or None."""
        for item in Query(self._query.limit(1), self._model_class, self._apply_filter):
            return item
        return None

    def one(self) -> T:
        """Fetch exactly one document. Raises if zero or more than one."""
        items = Query(self._query.limit(2), self._model_class, self._apply_filter).to_list()
        if not items:
            raise DocumentNotFoundError(self._model_class.__collection__, "<query>")
        if len(items) > 1:
            raise CendryError(
                f"Expected exactly one {self._model_class.__name__}, got more than one"
            )
        return items[0]

    def exists(self) -> bool:
        """Check if any matching documents exist."""
        return self.first() is not None

    def count(self) -> int:
        """Count matching documents using Firestore aggregation."""
        result = self._query.count().get()
        return result[0][0].value


class AsyncQuery[T: Model]:
    """Asynchronous query result with convenience methods.

    Immutable — filter() returns a new AsyncQuery.
    Reusable — each method creates a new stream.
    """

    def __init__(
        self,
        firestore_query: Any,
        model_class: type[T],
        apply_filter: Callable[[Any, Any], Any],
    ) -> None:
        self._query = firestore_query
        self._model_class = model_class
        self._apply_filter = apply_filter

    async def __aiter__(self) -> AsyncIterator[T]:
        async for doc in self._query.stream():
            yield deserialize(self._model_class, doc.id, doc.to_dict())

    def filter(self, *filters: Any) -> "AsyncQuery[T]":
        """Add filters to the query. Returns a new AsyncQuery."""
        query = self._query
        for f in filters:
            if isinstance(f, list):
                for sub in f:
                    query = self._apply_filter(query, sub)
            else:
                query = self._apply_filter(query, f)
        return AsyncQuery(query, self._model_class, self._apply_filter)

    async def to_list(self) -> list[T]:
        """Fetch all matching documents."""
        return [item async for item in self]

    async def first(self) -> T | None:
        """Fetch the first matching document, or None."""
        async for item in AsyncQuery(
            self._query.limit(1), self._model_class, self._apply_filter
        ):
            return item
        return None

    async def one(self) -> T:
        """Fetch exactly one document. Raises if zero or more than one."""
        items = await AsyncQuery(
            self._query.limit(2), self._model_class, self._apply_filter
        ).to_list()
        if not items:
            raise DocumentNotFoundError(self._model_class.__collection__, "<query>")
        if len(items) > 1:
            raise CendryError(
                f"Expected exactly one {self._model_class.__name__}, got more than one"
            )
        return items[0]

    async def exists(self) -> bool:
        """Check if any matching documents exist."""
        return (await self.first()) is not None

    async def count(self) -> int:
        """Count matching documents using Firestore aggregation."""
        result = await self._query.count().get()
        return result[0][0].value
