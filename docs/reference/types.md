# Types Reference

## `TypeRegistry`

Registry of Firestore-compatible types for `Field[T]` validation.

### `register(type_or_predicate)`

Register a type or predicate as Firestore-compatible.

```python
registry.register(MyType)
registry.register(lambda cls: hasattr(cls, "__custom__"))
```

### `validate(field_name, hint, class_name)`

Validate a type hint. Raises `TypeError` if not Firestore-compatible.

## `register_type`

Module-level convenience for `default_registry.register(...)`.

```python
from cendry import register_type

register_type(MyCustomClass)
```

## Default registry

Pre-populated with: scalars, Firestore SDK types, containers, structured types (Map, dataclass, TypedDict), enums, and optional third-party (pydantic, attrs, msgspec).
