# How to Extend Type Validation

`Field[T]` annotations are validated at class definition time. Only Firestore-compatible types are accepted — invalid types raise `TypeError` immediately, not at query time.

## Supported types

| Category | Types |
|----------|-------|
| Scalars | `str`, `int`, `float`, `bool`, `bytes`, `datetime.datetime` |
| Scalars with built-in handlers | `Decimal`, `datetime.date`, `datetime.time` |
| Firestore SDK | `GeoPoint`, `DocumentReference` |
| Containers | `list[T]`, `set[T]`, `tuple[T, ...]`, `dict[str, V]` |
| Structured | `Map`, dataclasses, `TypedDict` |
| Enums | `enum.Enum`, `IntEnum`, `StrEnum` |
| Optional | `T | None` |
| Third-party | pydantic, attrs, msgspec (if installed) |

### Built-in handlers

Firestore cannot store `Decimal`, `datetime.date`, or `datetime.time` natively. Cendry registers handlers for these types automatically — no manual registration needed.

| Python type | Stored as | Round-trip |
|-------------|-----------|------------|
| `Decimal` | `str` | Lossless |
| `datetime.date` | `datetime` at midnight UTC | Exact |
| `datetime.time` | `datetime` on 1970-01-01 UTC | Exact |

```python
class Event(Model, collection="events"):
    price: Field[Decimal]           # stored as "123.45"
    day: Field[datetime.date]       # stored as 2024-06-15T00:00:00Z
    start: Field[datetime.time]     # stored as 1970-01-01T14:30:00Z
```

!!! tip "Same convention as NDB"

    `datetime.date` and `datetime.time` follow Google NDB's `DateProperty` and `TimeProperty` conventions.

## Register a custom type with a handler

The handler tells Cendry how to convert your type to and from Firestore:

```python
from cendry import register_type

register_type(Money,
    serialize=lambda v: {"amount": v.amount, "currency": v.currency},
    deserialize=lambda v: Money(amount=v["amount"], currency=v["currency"]),
)
```

!!! tip "`deserialize` is required"

    Since Cendry reads from Firestore, you must provide `deserialize`. `serialize` is optional — it defaults to identity (passthrough) until writes are implemented.

### Full handler class

For complex behavior, subclass `BaseTypeHandler`:

```python
from cendry import BaseTypeHandler, register_type

class MoneyHandler(BaseTypeHandler):
    def serialize(self, value):
        return {"amount": value.amount, "currency": value.currency}

    def deserialize(self, value):
        return Money(amount=value["amount"], currency=value["currency"])

register_type(Money, handler=MoneyHandler())
```

### Predicate-based registration

For families of types:

```python
register_type(lambda cls: hasattr(cls, "__my_protocol__"),
    deserialize=lambda v: ...,
)
```

## Register a type without a handler

If you just need validation (the type is already handled by Firestore natively):

```python
register_type(MyCustomClass)
```

## Per-context registry

Override the type registry for a specific context:

```python
from cendry import TypeRegistry, Cendry

registry = TypeRegistry()
registry.register(MySpecialType, deserialize=lambda v: MySpecialType(v))

ctx = Cendry(type_registry=registry)
```

## Invalid types

These raise `TypeError` at class definition:

```python
class Bad(Model, collection="bad"):
    val: Field[complex]          # unsupported scalar
    data: Field[dict[int, str]]  # dict keys must be str
    city: Field[OtherModel]      # cannot nest Model
```

!!! info "Container elements are validated too"

    `Field[list[complex]]` is also rejected — validation recurses into container types.
