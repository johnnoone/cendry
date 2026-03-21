import dataclasses
import types
from typing import Any, get_args, get_type_hints

from .model import Map, Model


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


def deserialize_map(map_class: type, data: dict[str, Any]) -> Any:
    """Recursively deserialize a Map from a dict."""
    hints = get_type_hints(map_class, include_extras=True)
    converted: dict[str, Any] = {}
    for f in dataclasses.fields(map_class):
        value = data.get(f.name)
        if value is not None and isinstance(value, dict):
            inner = resolve_map_type(hints.get(f.name))
            if inner is not None:
                value = deserialize_map(inner, value)
        converted[f.name] = value
    return map_class(**converted)


def deserialize[T: Model](model_class: type[T], doc_id: str | None, data: dict[str, Any]) -> T:
    """Convert a dict to a model instance with nested Map deserialization."""
    hints = get_type_hints(model_class, include_extras=True)
    converted: dict[str, Any] = {}
    for f in dataclasses.fields(model_class):
        if f.name == "id":
            continue
        value = data.get(f.name)
        if value is not None and isinstance(value, dict):
            inner = resolve_map_type(hints.get(f.name))
            if inner is not None:
                value = deserialize_map(inner, value)
        converted[f.name] = value
    return model_class(id=doc_id, **converted)


def from_dict[T: Model](
    model_class: type[T],
    data: dict[str, Any],
    *,
    doc_id: str | None = None,
) -> T:
    """Construct a model instance from a dict.

    Raises TypeError if required fields are missing.
    """
    missing = [
        f.name
        for f in dataclasses.fields(model_class)
        if f.name != "id"
        and f.default is dataclasses.MISSING
        and f.default_factory is dataclasses.MISSING
        and f.name not in data
    ]
    if missing:
        fields = ", ".join(missing)
        raise TypeError(f"from_dict({model_class.__name__}): missing required fields: {fields}")
    return deserialize(model_class, doc_id, data)
