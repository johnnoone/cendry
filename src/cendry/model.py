import dataclasses
import types
from typing import Any, get_args, get_origin

from .filters import Filter


class FieldFilterResult(Filter):
    """A filter produced by a field descriptor method."""

    def __init__(self, field_name: str, op: str, value: Any) -> None:
        self.field_name = field_name
        self.op = op
        self.value = value


class FieldDescriptor:
    """Class-level descriptor for model fields.

    On class access: returns self (with filter methods).
    On instance access: returns the stored value.
    """

    def __init__(self, field_name: str) -> None:
        self.field_name = field_name

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        if obj is None:
            return self
        return obj.__dict__[self.field_name]

    def __set__(self, obj: Any, value: Any) -> None:
        obj.__dict__[self.field_name] = value

    def _make_filter(self, op: str, value: Any) -> FieldFilterResult:
        return FieldFilterResult(self.field_name, op, value)

    def eq(self, value: Any) -> FieldFilterResult:
        return self._make_filter("==", value)

    def ne(self, value: Any) -> FieldFilterResult:
        return self._make_filter("!=", value)

    def gt(self, value: Any) -> FieldFilterResult:
        return self._make_filter(">", value)

    def gte(self, value: Any) -> FieldFilterResult:
        return self._make_filter(">=", value)

    def lt(self, value: Any) -> FieldFilterResult:
        return self._make_filter("<", value)

    def lte(self, value: Any) -> FieldFilterResult:
        return self._make_filter("<=", value)

    def array_contains(self, value: Any) -> FieldFilterResult:
        return self._make_filter("array-contains", value)

    def array_contains_any(self, value: Any) -> FieldFilterResult:
        return self._make_filter("array-contains-any", value)

    def is_in(self, value: Any) -> FieldFilterResult:
        return self._make_filter("in", value)

    def not_in(self, value: Any) -> FieldFilterResult:
        return self._make_filter("not-in", value)


class Field[T]:
    """Type annotation marker for model fields.

    Used as Field[str], Field[int], etc. in model class annotations.
    At runtime, the metaclass replaces these with FieldDescriptor instances.
    """


def field(
    *,
    default: Any = dataclasses.MISSING,
    default_factory: Any = dataclasses.MISSING,
) -> Any:
    """Configure a model field with defaults."""
    kwargs: dict[str, Any] = {}
    if default is not dataclasses.MISSING:
        kwargs["default"] = default
    if default_factory is not dataclasses.MISSING:
        kwargs["default_factory"] = default_factory
    return dataclasses.field(**kwargs)


def _unwrap_field_type(hint: Any) -> Any:
    """Extract the inner type from Field[T]."""
    origin = get_origin(hint)
    args = get_args(hint)
    if origin is Field and args:
        return args[0]
    return hint  # pragma: no cover


def _get_inner_type(hint: Any) -> type | None:
    """Get the concrete inner type, unwrapping Field[T] and T | None."""
    inner = _unwrap_field_type(hint)
    origin = get_origin(inner)
    if origin is types.UnionType:
        non_none = [a for a in get_args(inner) if a is not type(None)]
        if len(non_none) == 1:
            inner = non_none[0]
    if isinstance(inner, type):
        return inner
    return None


def _validate_no_nested_models(cls: type, annotations: dict[str, Any]) -> None:
    """Raise TypeError if any field references a Model subclass."""
    for name, hint in annotations.items():
        inner = _get_inner_type(hint)
        if inner is not None and isinstance(inner, type) and issubclass(inner, Model):
            raise TypeError(
                f"Field '{name}' on '{cls.__name__}' cannot nest Model "
                f"'{inner.__name__}'. Use Map for embedded data."
            )


class _MapMeta(type):
    """Metaclass for Map that applies dataclass and sets up field descriptors."""

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> type:
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        if name in ("Map", "Model"):
            return cls

        # Rewrite Field[T] annotations to plain T for dataclasses
        raw_annotations = cls.__annotations__.copy()
        rewritten: dict[str, Any] = {
            attr_name: _unwrap_field_type(hint) for attr_name, hint in raw_annotations.items()
        }

        # For Model subclasses, inject `id` field if not already present
        is_model_subclass = any(
            b for b in bases if hasattr(b, "__collection__") or b.__name__ == "Model"
        )
        if is_model_subclass and "id" not in rewritten:
            rewritten["id"] = str | None
            cls.id = dataclasses.field(default=None, kw_only=True)  # type: ignore[attr-defined]

        cls.__annotations__ = rewritten

        _validate_no_nested_models(cls, raw_annotations)

        cls = dataclasses.dataclass(cls)  # type: ignore[arg-type,assignment]

        for f in dataclasses.fields(cls):  # type: ignore[arg-type]
            if f.name != "id":
                setattr(cls, f.name, FieldDescriptor(f.name))

        return cls


class Map(metaclass=_MapMeta):
    """Base class for embedded Firestore maps (nested data)."""


class Model(Map):
    """Base class for Firestore documents bound to a collection."""

    __collection__: str
    id: str | None = dataclasses.field(default=None, init=True)

    def __init_subclass__(cls, collection: str | None = None, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if collection is None:
            raise TypeError(
                f"Model '{cls.__name__}' must specify collection: "
                f"class {cls.__name__}(Model, collection='...')"
            )
        cls.__collection__ = collection
