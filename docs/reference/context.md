# Context Reference

## `Cendry`

Synchronous Firestore ODM context.

```python
Cendry(*, client: Client | None = None, type_registry: TypeRegistry | None = None)
```

Supports `with Cendry() as ctx:`.

### Methods

#### `get(model_class, document_id, *, parent=None) -> T`

Fetch a document by ID. Raises `DocumentNotFoundError` if not found.

#### `find(model_class, document_id, *, parent=None) -> T | None`

Fetch a document by ID. Returns `None` if not found.

#### `get_many(model_class, document_ids, *, parent=None) -> list[T]`

Batch fetch multiple documents. Raises `DocumentNotFoundError` if any are missing (error includes all missing IDs). Uses Firestore's `get_all()` for a single round trip.

#### `select(model_class, *filters, **kwargs) -> Query[T]`

Query documents. Returns a `Query` with chainable methods.

**Keyword arguments:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `order_by` | `list[Asc\|Desc]` | Ordering directives |
| `limit` | `int` | Max results |
| `start_at` | `dict \| Model` | Inclusive cursor |
| `start_after` | `dict \| Model` | Exclusive cursor |
| `end_at` | `dict \| Model` | Inclusive end cursor |
| `end_before` | `dict \| Model` | Exclusive end cursor |
| `parent` | `Model` | Parent document for subcollection |

#### `select_group(model_class, *filters, **kwargs) -> Query[T]`

Collection group query — across all subcollections with the given collection name.

---

## `AsyncCendry`

Asynchronous variant. Same API with `async`/`await`.

Supports `async with AsyncCendry() as ctx:`.

- `get`, `find`, `get_many` are `async def`
- `select`, `select_group` are regular `def` (return `AsyncQuery`)
