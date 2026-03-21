# API Reference

Everything is importable from `cendry`:

```python
from cendry import (
    # Models
    Model, Map, Field, field, FieldDescriptor,
    # Context
    Cendry, AsyncCendry,
    # Query
    Query, AsyncQuery, Asc, Desc,
    # Filters
    FieldFilter, And, Or,
    # Serialization
    from_dict, to_dict,
    # Type Registry
    TypeRegistry, register_type,
    # Exceptions
    CendryError, DocumentNotFoundError,
)
```

## Models

### `Model`

Base class for Firestore documents.

```python
class City(Model, collection="cities"):
    name: Field[str]
```

- `collection=` (required) — Firestore collection name
- Inherits `id: str | None` (document ID, defaults to `None`)
- All fields are keyword-only

### `Map`

Base class for embedded Firestore maps (nested data). No collection, no `id`.

### `Field[T]`

Type annotation for model fields. Dual behavior:
- Class access (`City.name`) → `FieldDescriptor` with filter/ordering methods
- Instance access (`city.name`) → `T` (the actual value)

### `field()`

Configure field defaults and metadata.

```python
field(default=None)
field(default_factory=list)
field(alias="firestoreName")
field(enum_by="name")  # or "value" (default)
```

### `FieldDescriptor`

Returned by class-level field access. Provides filter and ordering methods.

**Filter methods:** `eq()`, `ne()`, `gt()`, `gte()`, `lt()`, `lte()`, `array_contains()`, `array_contains_any()`, `is_in()`, `not_in()`

**Dunder shortcuts:** `==`, `!=`, `>`, `>=`, `<`, `<=`

**Ordering:** `asc()`, `desc()`

**Composition:** `&` (AND), `|` (OR)

## Context

### `Cendry`

Synchronous Firestore context.

```python
Cendry(*, client=None, type_registry=None)
```

**Methods:**
- `get(model_class, document_id, *, parent=None) -> T`
- `find(model_class, document_id, *, parent=None) -> T | None`
- `get_many(model_class, document_ids, *, parent=None) -> list[T]`
- `select(model_class, *filters, **kwargs) -> Query[T]`
- `select_group(model_class, *filters, **kwargs) -> Query[T]`

Supports `with Cendry() as ctx:`.

### `AsyncCendry`

Asynchronous Firestore context. Same API, `async` methods.

Supports `async with AsyncCendry() as ctx:`.

## Query

### `Query[T]`

Returned by `Cendry.select()` and `Cendry.select_group()`.

**Chainable (return new Query):**
- `filter(*filters) -> Query[T]`
- `order_by(*orders) -> Query[T]`
- `limit(n) -> Query[T]`

**Terminal (return results):**
- `to_list() -> list[T]`
- `first() -> T | None`
- `one() -> T` (raises if not exactly 1)
- `exists() -> bool`
- `count() -> int`
- `paginate(page_size) -> Iterator[list[T]]`

Iterable: `for item in query:`

### `AsyncQuery[T]`

Same API, async methods. Async iterable: `async for item in query:`

### `Asc` / `Desc`

Ordering directives. Prefer `City.population.asc()` over `Asc(City.population)`.

## Filters

### `FieldFilter`

Firestore's own filter class, re-exported.

```python
FieldFilter("state", "==", "CA")
```

### `And` / `Or`

Composite filters.

```python
And(City.state == "CA", City.population > 100)
Or(City.state == "CA", City.state == "NY")
```

## Serialization

### `from_dict(model_class, data, *, doc_id=None, by_alias=False) -> T`

Construct a model from a dict.

### `to_dict(instance, *, by_alias=False, include_id=False) -> dict`

Convert a model to a dict.

## Type Registry

### `TypeRegistry`

Registry of Firestore-compatible types.

### `register_type(type_or_predicate)`

Register a custom type or predicate in the global registry.

## Exceptions

### `CendryError`

Base exception for all Cendry errors.

### `DocumentNotFoundError`

Raised when a document is not found. Has `collection` and `document_id` attributes.
