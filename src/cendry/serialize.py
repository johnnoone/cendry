import dataclasses
import functools
import types
from typing import Any, get_args, get_type_hints

from .model import METADATA_ALIAS, Map, Model


@functools.cache
def _cached_type_hints(cls: type) -> dict[str, Any]:
    """Cache get_type_hints per class — avoids repeated MRO resolution."""
    return get_type_hints(cls, include_extras=True)


def _get_alias(f: dataclasses.Field[Any]) -> str:
    """Get the Firestore alias for a field, or its Python name."""
    result: str = f.metadata.get(METADATA_ALIAS, f.name)
    return result


def resolve_map_type(hint: Any) -> type | None:
    """Resolve a type hint to a concrete Map subclass if applicable."""
    if hint is None or isinstance(hint, str):
        return None
    if isinstance(hint, types.UnionType):
        non_none = [a for a in get_args(hint) if a is not type(None)]
        if len(non_none) == 1:
            hint = non_none[0]
    if isinstance(hint, type) and issubclass(hint, Map):
        return hint
    return None


def _deserialize_value(value: Any, hint: Any) -> Any:
    """Deserialize a single value, handling nested Maps."""
    if value is not None and isinstance(value, dict):
        inner = resolve_map_type(hint)
        if inner is not None:
            return deserialize_map(inner, value)
    return value


def deserialize_map(map_class: type, data: dict[str, Any]) -> Any:
    """Recursively deserialize a Map from a dict. Always reads by alias."""
    hints = _cached_type_hints(map_class)
    converted: dict[str, Any] = {}
    for f in dataclasses.fields(map_class):
        alias = _get_alias(f)
        value = _deserialize_value(data.get(alias), hints.get(f.name))
        converted[f.name] = value
    return map_class(**converted)


def deserialize[T: Model](model_class: type[T], doc_id: str | None, data: dict[str, Any]) -> T:
    """Convert a Firestore dict to a model instance. Always reads by alias."""
    hints = _cached_type_hints(model_class)
    converted: dict[str, Any] = {}
    for f in dataclasses.fields(model_class):
        if f.name == "id":
            continue
        alias = _get_alias(f)
        value = _deserialize_value(data.get(alias), hints.get(f.name))
        converted[f.name] = value
    return model_class(id=doc_id, **converted)


def from_dict[T: Model](
    model_class: type[T],
    data: dict[str, Any],
    *,
    doc_id: str | None = None,
    by_alias: bool = False,
) -> T:
    """Construct a model instance from a dict.

    Args:
        by_alias: If True, read from Firestore alias keys. If False (default), read from Python
                  field names.

    Raises TypeError if required fields are missing.
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
        return deserialize(model_class, doc_id, data)
    return deserialize(model_class, doc_id, remapped)


def _map_to_dict(instance: Map, *, by_alias: bool) -> dict[str, Any]:
    """Convert a Map instance to a dict recursively."""
    result: dict[str, Any] = {}
    for f in dataclasses.fields(instance):
        value = getattr(instance, f.name)
        key = _get_alias(f) if by_alias else f.name
        if isinstance(value, Map):  # pragma: no cover
            value = _map_to_dict(value, by_alias=by_alias)
        result[key] = value
    return result


def to_dict(
    instance: Model | Map,
    *,
    by_alias: bool = False,
    include_id: bool = False,
) -> dict[str, Any]:
    """Convert a model/map instance to a dict.

    Args:
        by_alias: If True, use Firestore alias keys. If False (default), use Python field names.
        include_id: If True, include the document ID in the output.
    """
    result = _map_to_dict(instance, by_alias=by_alias)
    if not include_id:
        result.pop("id", None)
    return result
