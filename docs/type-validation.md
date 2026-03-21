# Type Validation

`Field[T]` annotations are validated at class definition time. Only Firestore-compatible types are accepted — invalid types raise `TypeError` immediately.

## Supported Types

### Scalars

`str`, `int`, `float`, `bool`, `bytes`, `decimal.Decimal`, `datetime.datetime`

### Firestore SDK

`GeoPoint`, `DocumentReference`

### Containers

- `list[T]`, `set[T]`, `tuple[T1, T2, ...]` — inner types validated recursively
- `dict[str, V]` — keys must be `str`, value type validated

### Structured (map to Firestore maps)

- `Map` subclasses
- `@dataclass` classes
- `TypedDict`
- pydantic `BaseModel` (if installed)
- attrs classes (if installed)
- msgspec `Struct` (if installed)

### Enums

`enum.Enum`, `enum.IntEnum`, `enum.StrEnum` — all accepted automatically.

```python
import enum

class Status(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class User(Model, collection="users"):
    status: Field[Status]
```

### Optional

`T | None` — `T` is unwrapped and validated.

## Invalid Types

These raise `TypeError` at class definition:

```python
class Bad(Model, collection="bad"):
    val: Field[complex]       # TypeError: unsupported type 'complex'
    data: Field[dict[int, str]]  # TypeError: dict keys must be str
    city: Field[OtherModel]   # TypeError: cannot nest Model
```

## Custom Types

Register custom types as Firestore-compatible:

```python
from cendry import register_type

# Register a specific class
register_type(MyCustomClass)

# Register a predicate for a family of types
register_type(lambda cls: hasattr(cls, "__my_protocol__"))
```

## Per-Context Registry

Override the type registry for a specific context:

```python
from cendry import TypeRegistry, Cendry

registry = TypeRegistry()
registry.register(MySpecialType)

ctx = Cendry(type_registry=registry)
```
