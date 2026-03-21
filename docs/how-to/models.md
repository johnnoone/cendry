# How to Define Models

## Basic model

```python
from cendry import Model, Field

class City(Model, collection="cities"):
    name: Field[str]
    state: Field[str]
    population: Field[int]
```

The `collection=` parameter is required — Cendry never guesses collection names.

## Optional fields with defaults

```python
from cendry import field

class City(Model, collection="cities"):
    name: Field[str]
    nickname: Field[str | None] = field(default=None)
    tags: Field[list[str]] = field(default_factory=list)
```

## Embedded maps

Use `Map` for nested data (Firestore maps):

```python
from cendry import Map

class Address(Map):
    street: Field[str]
    city: Field[str]

class User(Model, collection="users"):
    name: Field[str]
    address: Field[Address]
```

Maps can nest other Maps. Maps have no `collection` and no `id`.

## Inheritance and mixins

```python
class TimestampMixin(Map):
    created_at: Field[datetime]
    updated_at: Field[datetime]

class City(TimestampMixin, Model, collection="cities"):
    name: Field[str]
```

All inherited fields work with filters, ordering, and serialization.

## Document ID

Every `Model` has `id: str | None`, defaulting to `None`:

```python
city = ctx.get(City, "SF")
print(city.id)  # "SF"
```

## Enum fields

```python
import enum

class Status(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class User(Model, collection="users"):
    status: Field[Status]
    role: Field[Role] = field(enum_by="name")  # store by name
```

## Restrictions

- `Model` cannot be nested inside another `Model` — use `Map`.
- Only [Firestore-compatible types](type-validation.md) are accepted in `Field[T]`.
