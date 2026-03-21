# How to Extend Type Validation

`Field[T]` annotations are validated at class definition time. Only Firestore-compatible types are accepted.

## Supported types

| Category | Types |
|----------|-------|
| Scalars | `str`, `int`, `float`, `bool`, `bytes`, `Decimal`, `datetime` |
| Firestore SDK | `GeoPoint`, `DocumentReference` |
| Containers | `list[T]`, `set[T]`, `tuple[T, ...]`, `dict[str, V]` |
| Structured | `Map`, dataclasses, `TypedDict` |
| Enums | `enum.Enum`, `IntEnum`, `StrEnum` |
| Optional | `T | None` |
| Third-party | pydantic, attrs, msgspec (if installed) |

## Register a custom type

```python
from cendry import register_type

register_type(MyCustomClass)
```

## Register a predicate

```python
register_type(lambda cls: hasattr(cls, "__my_protocol__"))
```

## Per-context registry

```python
from cendry import TypeRegistry, Cendry

registry = TypeRegistry()
registry.register(MySpecialType)

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
