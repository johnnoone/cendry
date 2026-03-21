# Models

## Model

`Model` represents a top-level Firestore document bound to a collection.

```python
from cendry import Model, Field, field

class City(Model, collection="cities"):
    name: Field[str]
    state: Field[str]
    country: Field[str]
    capital: Field[bool]
    population: Field[int]
    regions: Field[list[str]]
    nickname: Field[str | None] = field(default=None)
```

### Key properties

- `collection=` is **required** — no magic name derivation.
- All fields are **keyword-only** — `City(name="SF", state="CA", ...)`.
- Every `Model` has an `id: str | None` field (the Firestore document ID), defaulting to `None`.
- `Field[T]` is the type annotation. On instances, `city.name` returns `str`. On the class, `City.name` returns a `FieldDescriptor` with filter methods.

### Document ID

```python
city = ctx.get(City, "SF")
print(city.id)  # "SF"

# Create a model with an explicit ID
city = City(name="SF", state="CA", ..., id="SF")
```

## Map

`Map` represents embedded data (a Firestore map). It has no collection, no `id`.

```python
from cendry import Map, Field

class Mayor(Map):
    name: Field[str]
    since: Field[int]

class City(Model, collection="cities"):
    name: Field[str]
    mayor: Field[Mayor | None] = field(default=None)
```

When Firestore returns `{"mayor": {"name": "Jane", "since": 2020}}`, the `mayor` field is automatically deserialized into a `Mayor` instance.

`Map` can nest other `Map`s:

```python
class Address(Map):
    street: Field[str]
    city: Field[str]

class Person(Map):
    name: Field[str]
    address: Field[Address]
```

## Field Defaults

Use `field()` to configure defaults:

```python
from cendry import field

class City(Model, collection="cities"):
    name: Field[str]
    nickname: Field[str | None] = field(default=None)
    tags: Field[list[str]] = field(default_factory=list)
```

## Field Aliases

When the Firestore field name differs from the Python attribute name:

```python
class City(Model, collection="cities"):
    name: Field[str] = field(alias="displayName")
```

- `city.name` accesses the Python attribute
- Firestore stores and reads from `"displayName"`
- Filters use the alias: `City.name == "SF"` generates `FieldFilter("displayName", "==", "SF")`

## Inheritance and Mixins

Models can inherit from other `Map` classes (mixins):

```python
class TimestampMixin(Map):
    created_at: Field[datetime]
    updated_at: Field[datetime]

class City(TimestampMixin, Model, collection="cities"):
    name: Field[str]
    state: Field[str]
```

All inherited fields work with filters, ordering, and serialization.

## Restrictions

- A `Model` **cannot** be nested inside another `Model` via `Field[SomeModel]` — use `Map` for embedded data.
- Only [Firestore-compatible types](type-validation.md) are accepted in `Field[T]`.
