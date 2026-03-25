# Models Reference

## `Model`

Base class for Firestore documents.

```python
class City(Model, collection="cities"):
    name: Field[str]
```

**Class parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `collection` | `str` | Firestore collection name (required) |

**Inherited attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | `str \| None` | Document ID, defaults to `None` |
| `__collection__` | `ClassVar[str]` | The collection name |

## `Map`

Base class for embedded Firestore maps. No collection, no `id`.

```python
class Address(Map):
    street: Field[str]
    city: Field[str]
```

## `Field[T]`

Type annotation for model fields. Dual behavior:

- **Class access** (`City.name`) returns `FieldDescriptor`
- **Instance access** (`city.name`) returns `T`

## `FieldDescriptor`

Returned by class-level field access. Provides:

**Filter methods:**

| Method | Operator |
|--------|----------|
| `.eq(value)` | `==` |
| `.ne(value)` | `!=` |
| `.gt(value)` | `>` |
| `.gte(value)` | `>=` |
| `.lt(value)` | `<` |
| `.lte(value)` | `<=` |
| `.array_contains(value)` | `array-contains` |
| `.array_contains_any(values)` | `array-contains-any` |
| `.is_in(values)` | `in` |
| `.not_in(values)` | `not-in` |

**Dunder shortcuts:** `==`, `!=`, `>`, `>=`, `<`, `<=`

**Ordering:** `.asc()`, `.desc()`

**Composition:** `&` (AND), `|` (OR)

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `field_name` | `str` | Python attribute name |
| `alias` | `str` | Firestore field name (defaults to `field_name`) |
| `owner` | `type` | The model class this descriptor belongs to |

## `field()`

```python
field(
    *,
    default=MISSING,
    default_factory=MISSING,
    alias: str | None = None,
    enum_by: str = "value",
    auto_now: bool = False,
    auto_now_add: bool = False,
) -> Any
```

| Parameter | Description |
|-----------|-------------|
| `default` | Default value |
| `default_factory` | Callable that returns the default |
| `alias` | Firestore field name (if different from Python name) |
| `enum_by` | `"value"` (default) or `"name"` for enum storage |
| `auto_now` | If `True`, always set to current UTC time on `save()`/`create()` |
| `auto_now_add` | If `True`, set to current UTC time on `save()`/`create()` only if `None` |
