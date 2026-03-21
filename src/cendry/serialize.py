import dataclasses
import functools
import types
from typing import Any, get_args, get_origin, get_type_hints

from .model import METADATA_ALIAS, METADATA_ENUM_BY, Map, Model
from .types import TypeRegistry, default_registry


@functools.cache
def _cached_type_hints(cls: type) -> dict[str, Any]:
    """Cache get_type_hints per class — avoids repeated MRO resolution."""
    return get_type_hints(cls, include_extras=True)


def _get_alias(f: dataclasses.Field[Any]) -> str:
    """Get the Firestore alias for a field, or its Python name."""
    result: str = f.metadata.get(METADATA_ALIAS, f.name)
    return result


def _resolve_inner_type(hint: Any) -> type | None:
    """Resolve a type hint to a concrete type, unwrapping Optional."""
    if hint is None or isinstance(hint, str):
        return None
    if isinstance(hint, types.UnionType):
        non_none = [a for a in get_args(hint) if a is not type(None)]
        if len(non_none) == 1:
            hint = non_none[0]
    if isinstance(hint, type):
        return hint
    return None


def resolve_map_type(hint: Any) -> type | None:
    """Resolve a type hint to a concrete Map subclass if applicable."""
    inner = _resolve_inner_type(hint)
    if inner is not None and issubclass(inner, Map):
        return inner
    return None


def _deserialize_value(
    value: Any, hint: Any, *, enum_by: str = "value", registry: TypeRegistry
) -> Any:
    """Deserialize a single value, checking handlers, enums, then Map nesting.

    Handles containers: list[Money] deserializes each element via MoneyHandler.
    """
    import enum

    if value is None:
        return None

    # Direct type match (non-container)
    inner_type = _resolve_inner_type(hint)
    if inner_type is not None:
        handler = registry.get_handler(inner_type)
        if handler is not None:
            return handler.deserialize(value)
        # Enum conversion
        if isinstance(inner_type, type) and issubclass(inner_type, enum.Enum):
            if enum_by == "name":
                return inner_type[value]
            return inner_type(value)

    # Container types: recurse into elements
    origin = get_origin(hint)
    if origin in (list, set, tuple) and isinstance(value, (list, set, tuple)):
        args = get_args(hint)
        if args:
            if origin is tuple:  # pragma: no cover
                return tuple(
                    _deserialize_value(v, a, registry=registry)
                    for v, a in zip(value, args, strict=False)
                )
            elem_hint = args[0]
            converted = [_deserialize_value(v, elem_hint, registry=registry) for v in value]
            return set(converted) if origin is set else converted
    if origin is dict and isinstance(value, dict):
        args = get_args(hint)
        if args and len(args) > 1:
            val_hint = args[1]
            return {
                k: _deserialize_value(v, val_hint, registry=registry)
                for k, v in value.items()
            }

    # Map nesting
    if isinstance(value, dict):
        inner = resolve_map_type(hint)
        if inner is not None:
            return deserialize_map(inner, value, registry=registry)
    return value


def _get_enum_by(f: dataclasses.Field[Any]) -> str:
    """Get enum_by setting from field metadata. Defaults to 'value'."""
    if f.metadata:
        result: str = f.metadata.get(METADATA_ENUM_BY, "value")
        return result
    return "value"


def deserialize_map(map_class: type, data: dict[str, Any], *, registry: TypeRegistry) -> Any:
    """Recursively deserialize a Map from a dict. Always reads by alias."""
    hints = _cached_type_hints(map_class)
    converted: dict[str, Any] = {}
    for f in dataclasses.fields(map_class):
        alias = _get_alias(f)
        value = _deserialize_value(
            data.get(alias), hints.get(f.name), enum_by=_get_enum_by(f), registry=registry
        )
        converted[f.name] = value
    return map_class(**converted)


def deserialize[T: Model](
    model_class: type[T],
    doc_id: str | None,
    data: dict[str, Any],
    *,
    registry: TypeRegistry | None = None,
) -> T:
    """Convert a Firestore dict to a model instance. Always reads by alias."""
    registry = registry or default_registry
    hints = _cached_type_hints(model_class)
    converted: dict[str, Any] = {}
    for f in dataclasses.fields(model_class):
        if f.name == "id":
            continue
        alias = _get_alias(f)
        value = _deserialize_value(
            data.get(alias), hints.get(f.name), enum_by=_get_enum_by(f), registry=registry
        )
        converted[f.name] = value
    return model_class(id=doc_id, **converted)


def from_dict[T: Model](
    model_class: type[T],
    data: dict[str, Any],
    *,
    doc_id: str | None = None,
    by_alias: bool = False,
    registry: TypeRegistry | None = None,
) -> T:
    """Construct a model instance from a dict.

    Nested `Map` dicts are automatically converted to their respective classes.

    Args:
        model_class: The Model class to construct.
        data: Dict of field values.
        doc_id: Optional document ID.
        by_alias: If True, read keys by Firestore alias. If False (default), use Python names.

    Returns:
        The constructed model instance.

    Raises:
        TypeError: If required fields are missing.
    """
    missing = []
    remapped: dict[str, Any] = {}
    for f in dataclasses.fields(model_class):
        if f.name == "id":
            continue
        alias = _get_alias(f)
        key = alias if by_alias else f.name
        has_default = (
            f.default is not dataclasses.MISSING or f.default_factory is not dataclasses.MISSING
        )
        if key not in data and not has_default:
            missing.append(f.name)
        elif not by_alias and f.name in data:
            remapped[alias] = data[f.name]
    if missing:
        fields = ", ".join(missing)
        raise TypeError(f"from_dict({model_class.__name__}): missing required fields: {fields}")
    if by_alias:
        return deserialize(model_class, doc_id, data, registry=registry)
    return deserialize(model_class, doc_id, remapped, registry=registry)


def _serialize_value(
    value: Any, hint: Any, *, by_alias: bool, enum_by: str = "value", registry: TypeRegistry
) -> Any:
    """Serialize a single value, checking handlers, enums, then Map nesting.

    Handles containers: list[Money] serializes each element via MoneyHandler.
    """
    import enum as enum_mod

    if value is None:
        return None

    # Direct type match
    inner_type = _resolve_inner_type(hint)
    if inner_type is not None:
        handler = registry.get_handler(inner_type)
        if handler is not None:
            return handler.serialize(value)
        # Enum conversion
        if isinstance(value, enum_mod.Enum):
            return value.name if enum_by == "name" else value.value

    # Container types: recurse into elements
    origin = get_origin(hint)
    if origin in (list, set, tuple) and isinstance(value, (list, set, tuple)):
        args = get_args(hint)
        if args:
            if origin is tuple:  # pragma: no cover
                return [
                    _serialize_value(v, a, by_alias=by_alias, registry=registry)
                    for v, a in zip(value, args, strict=False)
                ]
            elem_hint = args[0]
            return [
                _serialize_value(v, elem_hint, by_alias=by_alias, registry=registry)
                for v in value
            ]
    if origin is dict and isinstance(value, dict):
        args = get_args(hint)
        if args and len(args) > 1:
            val_hint = args[1]
            return {
                k: _serialize_value(v, val_hint, by_alias=by_alias, registry=registry)
                for k, v in value.items()
            }

    # Map nesting
    if isinstance(value, Map):
        return _map_to_dict(value, by_alias=by_alias, registry=registry)
    return value


def _map_to_dict(
    instance: Map, *, by_alias: bool, registry: TypeRegistry
) -> dict[str, Any]:
    """Convert a Map instance to a dict recursively."""
    hints = _cached_type_hints(type(instance))
    result: dict[str, Any] = {}
    for f in dataclasses.fields(instance):
        value = getattr(instance, f.name)
        key = _get_alias(f) if by_alias else f.name
        value = _serialize_value(
            value,
            hints.get(f.name),
            by_alias=by_alias,
            enum_by=_get_enum_by(f),
            registry=registry,
        )
        result[key] = value
    return result


def to_dict(
    instance: Model | Map,
    *,
    by_alias: bool = False,
    include_id: bool = False,
    registry: TypeRegistry | None = None,
) -> dict[str, Any]:
    """Convert a model/map instance to a dict.

    Nested `Map` instances are recursively converted to dicts.

    Args:
        instance: Model or Map instance to convert.
        by_alias: If True, use Firestore alias keys. If False (default), use Python field names.
        include_id: If True, include the document ID in the output.
        registry: Optional TypeRegistry. Uses default if not provided.

    Returns:
        Dict representation of the instance.
    """
    registry = registry or default_registry
    result = _map_to_dict(instance, by_alias=by_alias, registry=registry)
    if not include_id:
        result.pop("id", None)
    return result
