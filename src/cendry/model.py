import dataclasses
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    dataclass_transform,
    get_args,
    get_origin,
    overload,
)

from .filters import Filter

if TYPE_CHECKING:
    from .query import Asc, Desc

# Maps operator strings to dunder symbols for repr
_DUNDER_OPS: dict[str, str] = {"==": "==", "!=": "!=", ">": ">", ">=": ">=", "<": "<", "<=": "<="}
_METHOD_OPS: dict[str, str] = {
    "array-contains": "array_contains",
    "array-contains-any": "array_contains_any",
    "in": "is_in",
    "not-in": "not_in",
}


class FieldFilterResult(Filter):
    """A filter produced by a field descriptor method."""

    def __init__(
        self,
        field_name: str,
        op: str,
        value: Any,
        *,
        owner: type | None = None,
        python_name: str | None = None,
    ) -> None:
        self.field_name = field_name  # alias (for Firestore)
        self.op = op
        self.value = value
        self._owner = owner
        self._python_name = python_name or field_name

    def __repr__(self) -> str:
        owner = f"{self._owner.__name__}." if self._owner else ""
        field = self._python_name
        if self.op in _DUNDER_OPS:
            return f"{owner}{field} {_DUNDER_OPS[self.op]} {self.value!r}"
        if self.op in _METHOD_OPS:
            return f"{owner}{field}.{_METHOD_OPS[self.op]}({self.value!r})"
        return f'FieldFilter("{self.field_name}", "{self.op}", {self.value!r})'  # pragma: no cover


class FieldDescriptor:
    """Runtime descriptor installed on model classes by the metaclass.

    On class access: returns self (with filter methods).
    On instance access: returns the stored value.
    """

    def __init__(
        self,
        field_name: str,
        *,
        alias: str | None = None,
        owner: type | None = None,
    ) -> None:
        self.field_name = field_name
        self.alias = alias or field_name
        self.owner = owner

    def __repr__(self) -> str:
        owner_name = self.owner.__name__ if self.owner else "?"
        return f"{owner_name}.{self.field_name}"

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        if obj is None:
            return self
        return obj.__dict__[self.field_name]

    def __set__(self, obj: Any, value: Any) -> None:
        obj.__dict__[self.field_name] = value

    def _make_filter(self, op: str, value: Any) -> FieldFilterResult:
        return FieldFilterResult(
            self.alias, op, value, owner=self.owner, python_name=self.field_name
        )

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

    # Dunder shortcuts
    __hash__ = None  # type: ignore[assignment]

    def __eq__(self, other: object) -> FieldFilterResult:  # type: ignore[override]
        return self._make_filter("==", other)

    def __ne__(self, other: object) -> FieldFilterResult:  # type: ignore[override]
        return self._make_filter("!=", other)

    def __gt__(self, other: Any) -> FieldFilterResult:
        return self._make_filter(">", other)

    def __ge__(self, other: Any) -> FieldFilterResult:
        return self._make_filter(">=", other)

    def __lt__(self, other: Any) -> FieldFilterResult:
        return self._make_filter("<", other)

    def __le__(self, other: Any) -> FieldFilterResult:
        return self._make_filter("<=", other)

    # Ordering
    def asc(self) -> "Asc":
        from .query import Asc

        return Asc(self)

    def desc(self) -> "Desc":
        from .query import Desc

        return Desc(self)


class Field[T]:
    """Typed field descriptor for Model and Map classes.

    Used as ``Field[str]``, ``Field[int]``, etc. in class annotations.
    At runtime, the metaclass replaces Field annotations with FieldDescriptor instances.

    The overloaded ``__get__`` tells type checkers:
    - Class access (``City.state``) returns ``FieldDescriptor`` (with ``.eq()``, ``.gt()``, etc.)
    - Instance access (``city.state``) returns ``T`` (the actual value)
    """

    @overload
    def __get__(self, obj: None, objtype: type) -> FieldDescriptor: ...
    @overload
    def __get__(self, obj: Any, objtype: type | None = None) -> T: ...

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:  # pragma: no cover
        # Never called at runtime — the metaclass replaces Field with FieldDescriptor
        raise NotImplementedError


def field(
    *,
    default: Any = dataclasses.MISSING,
    default_factory: Any = dataclasses.MISSING,
    alias: str | None = None,
    enum_by: str = "value",
) -> Any:
    """Configure a model field with defaults and metadata."""
    metadata: dict[str, Any] = {}
    if alias is not None:
        metadata["cendry_alias"] = alias
    if enum_by != "value":
        metadata["cendry_enum_by"] = enum_by
    kwargs: dict[str, Any] = {}
    if default is not dataclasses.MISSING:
        kwargs["default"] = default
    if default_factory is not dataclasses.MISSING:
        kwargs["default_factory"] = default_factory
    if metadata:
        kwargs["metadata"] = metadata
    return dataclasses.field(**kwargs)


def _unwrap_field_type(hint: Any) -> Any:
    """Extract the inner type from Field[T]."""
    origin = get_origin(hint)
    args = get_args(hint)
    if origin is Field and args:
        return args[0]
    return hint  # pragma: no cover


@dataclass_transform(kw_only_default=True, field_specifiers=(Field, field))
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
            cls.id = dataclasses.field(default=None)  # type: ignore[attr-defined]  # mypy: dynamic attr on metaclass

        cls.__annotations__ = rewritten

        from .types import default_registry

        for attr_name, hint in raw_annotations.items():
            inner = _unwrap_field_type(hint)
            default_registry.validate(attr_name, inner, name)

        cls = dataclasses.dataclass(kw_only=True)(cls)  # type: ignore[arg-type,assignment]  # mypy: metaclass type mismatch

        for f in dataclasses.fields(cls):  # type: ignore[arg-type]  # mypy: metaclass type mismatch
            if f.name != "id":
                alias = f.metadata.get("cendry_alias") if f.metadata else None
                setattr(cls, f.name, FieldDescriptor(f.name, alias=alias, owner=cls))

        return cls


class Map(metaclass=_MapMeta):
    """Base class for embedded Firestore maps (nested data)."""


class Model(Map):
    """Base class for Firestore documents bound to a collection."""

    __collection__: ClassVar[str]
    id: str | None = dataclasses.field(default=None)

    def __init_subclass__(cls, collection: str | None = None, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if collection is None:
            raise TypeError(
                f"class {cls.__name__}(Model) requires a collection name.\n"
                f'  Example: class {cls.__name__}(Model, collection="{cls.__name__.lower()}s")'
            )
        cls.__collection__ = collection
