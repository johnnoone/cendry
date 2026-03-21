# How to Define Models

## Basic model

Every model needs a `collection=` — Cendry never guesses collection names.

```python
from cendry import Model, Field

class City(Model, collection="cities"):
    name: Field[str]
    state: Field[str]
    population: Field[int]
```

## Optional fields with defaults

Use `field()` for defaults. Fields without defaults are required.

```python
from cendry import field

class City(Model, collection="cities"):
    name: Field[str]
    nickname: Field[str | None] = field(default=None)
    tags: Field[list[str]] = field(default_factory=list)
```

## Embedded maps

Use `Map` for nested data — Firestore maps within a document.

```python
from cendry import Map

class Address(Map):
    street: Field[str]
    city: Field[str]

class User(Model, collection="users"):
    name: Field[str]
    address: Field[Address]
```

Maps can nest other Maps. They have no `collection` and no `id`.

!!! info

    When Firestore returns `{"address": {"street": "123 Main", "city": "SF"}}`, the `address` field is automatically deserialized into an `Address` instance.

## Inheritance and mixins

Share fields across models using `Map` as a mixin:

```python
from datetime import datetime

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

Enums are supported and auto-converted:

```python
import enum

class Status(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class User(Model, collection="users"):
    status: Field[Status]                          # stores by value: "active"
    role: Field[Role] = field(enum_by="name")      # stores by name: "ADMIN"
```

!!! tip

    `IntEnum` and `StrEnum` also work. The `enum_by` setting controls whether the value or the name is stored in Firestore.

## Field aliases

When the Firestore field name differs from the Python name:

```python
class City(Model, collection="cities"):
    name: Field[str] = field(alias="displayName")
```

See [How to Use Aliases](aliases.md) for details.

## Restrictions

!!! warning "What you can't do"

    - **Model inside Model** — `Field[OtherModel]` raises `TypeError`. Use `Map` for embedded data.
    - **Unsupported types** — `Field[complex]` and other non-Firestore types raise `TypeError` at class definition.
    - **Dict keys must be `str`** — `Field[dict[int, str]]` is rejected.
