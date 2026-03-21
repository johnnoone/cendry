# Query Reference

## `Query[T]`

Returned by `Cendry.select()` and `Cendry.select_group()`. Immutable and reusable.

### Chainable methods (return new Query)

#### `filter(*filters) -> Query[T]`

Add filters. Accepts `FieldFilterResult`, `FieldFilter`, `And`, `Or`, or a `list` of filters.

#### `order_by(*orders) -> Query[T]`

Add ordering. Accepts `FieldDescriptor` (ascending by default), `Asc`, or `Desc`. Multiple calls append.

#### `limit(n: int) -> Query[T]`

Limit the number of results.

### Terminal methods (return results)

#### `to_list() -> list[T]`

Fetch all matching documents.

#### `first() -> T | None`

Fetch the first matching document, or `None`. Uses `limit(1)` internally.

#### `one() -> T`

Fetch exactly one document. Raises `DocumentNotFoundError` if none, `CendryError` if more than one.

#### `exists() -> bool`

Check if any matching documents exist. Uses `limit(1)` internally.

#### `count() -> int`

Count matching documents using Firestore's aggregation API (no document fetch).

#### `paginate(page_size: int) -> Iterator[list[T]]`

Iterate over pages. Each page is a `list[T]`. Stops when a page has fewer items than `page_size`.

### Iteration

```python
for item in query:
    ...
```

---

## `AsyncQuery[T]`

Async variant. Same chainable methods (`filter`, `order_by`, `limit` are sync — they return `AsyncQuery`). Terminal methods are `async def`. Supports `async for`.

---

## `Asc`

```python
Asc(field: str | FieldDescriptor)
```

Ascending order. Prefer `City.population.asc()`.

## `Desc`

```python
Desc(field: str | FieldDescriptor)
```

Descending order. Prefer `City.population.desc()`.
