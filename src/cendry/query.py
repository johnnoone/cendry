from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any

from .exceptions import CendryError, DocumentNotFoundError
from .model import FieldDescriptor, Model
from .serialize import deserialize
from .types import TypeRegistry, default_registry


class _Order:
    """Base class for ordering directives."""

    direction: str

    def __init__(self, field: str | FieldDescriptor) -> None:
        if isinstance(field, FieldDescriptor):
            self.field = field.alias  # use alias for Firestore
            self._owner = field.owner
            self._python_name = field.field_name
        else:
            self.field = field
            self._owner = None
            self._python_name = field


class Asc(_Order):
    """Ascending order."""

    direction = "ASCENDING"

    def __repr__(self) -> str:
        if self._owner:
            return f"{self._owner.__name__}.{self._python_name}.asc()"
        return f'Asc("{self.field}")'


class Desc(_Order):
    """Descending order."""

    direction = "DESCENDING"

    def __repr__(self) -> str:
        if self._owner:
            return f"{self._owner.__name__}.{self._python_name}.desc()"
        return f'Desc("{self.field}")'


class Query[T: Model]:
    """Synchronous query result with convenience methods.

    Immutable — filter(), order_by(), limit() return a new Query.
    Reusable — each method creates a new stream.
    """

    def __init__(
        self,
        firestore_query: Any,
        model_class: type[T],
        apply_filter: Callable[[Any, Any], Any],
        *,
        registry: TypeRegistry | None = None,
        _filters: list[Any] | None = None,
        _order_by: list[Any] | None = None,
        _limit: int | None = None,
    ) -> None:
        self._query = firestore_query
        self._model_class = model_class
        self._apply_filter = apply_filter
        self._registry = registry or default_registry
        self._filters_repr = _filters or []
        self._order_by_repr = _order_by or []
        self._limit_repr = _limit

    def __repr__(self) -> str:
        parts: list[str] = [self._model_class.__name__]
        parts.extend(repr(f) for f in self._filters_repr)
        if self._order_by_repr:
            parts.append(f"order_by=[{', '.join(repr(o) for o in self._order_by_repr)}]")
        if self._limit_repr is not None:
            parts.append(f"limit={self._limit_repr}")
        return f"Query({', '.join(parts)})"

    def __iter__(self) -> Iterator[T]:
        for doc in self._query.stream():
            yield deserialize(self._model_class, doc.id, doc.to_dict(), registry=self._registry)

    def filter(self, *filters: Any) -> "Query[T]":
        """Add filters to the query. Returns a new Query."""
        query = self._query
        new_filters = list(self._filters_repr)
        for f in filters:
            if isinstance(f, list):
                for sub in f:
                    query = self._apply_filter(query, sub)
                    new_filters.append(sub)
            else:
                query = self._apply_filter(query, f)
                new_filters.append(f)
        return Query(
            query,
            self._model_class,
            self._apply_filter,
            registry=self._registry,
            _filters=new_filters,
            _order_by=self._order_by_repr,
            _limit=self._limit_repr,
        )

    def order_by(self, *orders: Any) -> "Query[T]":
        """Add ordering. Accepts FieldDescriptor (ascending), Asc, or Desc."""
        query = self._query
        new_orders = list(self._order_by_repr)
        for order in orders:
            if isinstance(order, FieldDescriptor):
                order = Asc(order)
            query = query.order_by(order.field, direction=order.direction)
            new_orders.append(order)
        return Query(
            query,
            self._model_class,
            self._apply_filter,
            registry=self._registry,
            _filters=self._filters_repr,
            _order_by=new_orders,
            _limit=self._limit_repr,
        )

    def limit(self, n: int) -> "Query[T]":
        """Limit the number of results. Returns a new Query."""
        return Query(
            self._query.limit(n),
            self._model_class,
            self._apply_filter,
            registry=self._registry,
            _filters=self._filters_repr,
            _order_by=self._order_by_repr,
            _limit=n,
        )

    def to_list(self) -> list[T]:
        """Fetch all matching documents."""
        return list(self)

    def first(self) -> T | None:
        """Fetch the first matching document, or None."""
        for item in Query(
            self._query.limit(1), self._model_class, self._apply_filter, registry=self._registry
        ):
            return item
        return None

    def one(self) -> T:
        """Fetch exactly one document. Raises if zero or more than one."""
        items = Query(
            self._query.limit(2), self._model_class, self._apply_filter, registry=self._registry
        ).to_list()
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
        return int(result[0][0].value)

    def paginate(self, page_size: int) -> Iterator[list[T]]:
        """Iterate over pages of results."""
        query = self._query
        while True:
            items: list[T] = []
            last_doc = None
            for doc in query.limit(page_size).stream():
                last_doc = doc
                items.append(
                    deserialize(self._model_class, doc.id, doc.to_dict(), registry=self._registry)
                )
            if not items:
                break
            yield items
            if len(items) < page_size:
                break
            query = query.start_after(last_doc)


class AsyncQuery[T: Model]:
    """Asynchronous query result with convenience methods.

    Immutable — filter(), order_by(), limit() return a new AsyncQuery.
    Reusable — each method creates a new stream.
    """

    def __init__(
        self,
        firestore_query: Any,
        model_class: type[T],
        apply_filter: Callable[[Any, Any], Any],
        *,
        registry: TypeRegistry | None = None,
        _filters: list[Any] | None = None,
        _order_by: list[Any] | None = None,
        _limit: int | None = None,
    ) -> None:
        self._query = firestore_query
        self._model_class = model_class
        self._apply_filter = apply_filter
        self._registry = registry or default_registry
        self._filters_repr = _filters or []
        self._order_by_repr = _order_by or []
        self._limit_repr = _limit

    def __repr__(self) -> str:
        parts: list[str] = [self._model_class.__name__]
        parts.extend(repr(f) for f in self._filters_repr)
        if self._order_by_repr:
            parts.append(f"order_by=[{', '.join(repr(o) for o in self._order_by_repr)}]")
        if self._limit_repr is not None:
            parts.append(f"limit={self._limit_repr}")
        return f"AsyncQuery({', '.join(parts)})"

    async def __aiter__(self) -> AsyncIterator[T]:
        async for doc in self._query.stream():
            yield deserialize(self._model_class, doc.id, doc.to_dict(), registry=self._registry)

    def filter(self, *filters: Any) -> "AsyncQuery[T]":
        """Add filters to the query. Returns a new AsyncQuery."""
        query = self._query
        new_filters = list(self._filters_repr)
        for f in filters:
            if isinstance(f, list):
                for sub in f:
                    query = self._apply_filter(query, sub)
                    new_filters.append(sub)
            else:
                query = self._apply_filter(query, f)
                new_filters.append(f)
        return AsyncQuery(
            query,
            self._model_class,
            self._apply_filter,
            registry=self._registry,
            _filters=new_filters,
            _order_by=self._order_by_repr,
            _limit=self._limit_repr,
        )

    def order_by(self, *orders: Any) -> "AsyncQuery[T]":
        """Add ordering. Accepts FieldDescriptor (ascending), Asc, or Desc."""
        query = self._query
        new_orders = list(self._order_by_repr)
        for order in orders:
            if isinstance(order, FieldDescriptor):
                order = Asc(order)
            query = query.order_by(order.field, direction=order.direction)
            new_orders.append(order)
        return AsyncQuery(
            query,
            self._model_class,
            self._apply_filter,
            registry=self._registry,
            _filters=self._filters_repr,
            _order_by=new_orders,
            _limit=self._limit_repr,
        )

    def limit(self, n: int) -> "AsyncQuery[T]":
        """Limit the number of results. Returns a new AsyncQuery."""
        return AsyncQuery(
            self._query.limit(n),
            self._model_class,
            self._apply_filter,
            registry=self._registry,
            _filters=self._filters_repr,
            _order_by=self._order_by_repr,
            _limit=n,
        )

    async def to_list(self) -> list[T]:
        """Fetch all matching documents."""
        return [item async for item in self]

    async def first(self) -> T | None:
        """Fetch the first matching document, or None."""
        async for item in AsyncQuery(
            self._query.limit(1), self._model_class, self._apply_filter, registry=self._registry
        ):
            return item
        return None

    async def one(self) -> T:
        """Fetch exactly one document. Raises if zero or more than one."""
        items = await AsyncQuery(
            self._query.limit(2),
            self._model_class,
            self._apply_filter,
            registry=self._registry,
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
        return int(result[0][0].value)

    async def paginate(self, page_size: int) -> AsyncIterator[list[T]]:
        """Iterate over pages of results."""
        query = self._query
        while True:
            items: list[T] = []
            last_doc = None
            async for doc in query.limit(page_size).stream():
                last_doc = doc
                items.append(
                    deserialize(self._model_class, doc.id, doc.to_dict(), registry=self._registry)
                )
            if not items:
                break
            yield items
            if len(items) < page_size:
                break
            query = query.start_after(last_doc)
