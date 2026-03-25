import dataclasses
import datetime
import enum
import types
from collections.abc import Callable
from decimal import Decimal
from typing import Any, Protocol, get_args, get_origin, is_typeddict, runtime_checkable

from google.cloud.firestore_v1._helpers import GeoPoint
from google.cloud.firestore_v1.document import DocumentReference

_SCALAR_TYPES: frozenset[type] = frozenset(
    {
        str,
        int,
        float,
        bool,
        bytes,
        Decimal,
        datetime.datetime,
        datetime.date,
        datetime.time,
        GeoPoint,
        DocumentReference,
    }
)

_CONTAINER_TYPES: frozenset[type] = frozenset({list, tuple, set, dict})


@runtime_checkable
class TypeHandler(Protocol):
    """Protocol defining the contract for type handlers.

    Any class implementing ``serialize`` and ``deserialize`` satisfies this protocol.
    """

    def serialize(self, value: Any) -> Any: ...
    def deserialize(self, value: Any) -> Any: ...


class BaseTypeHandler:
    """Base class with sensible defaults.

    Subclass and override what you need. New methods can be added
    in the future without breaking existing handlers.
    """

    def serialize(self, value: Any) -> Any:
        """Convert a Python value to a Firestore-compatible value."""
        return value

    def deserialize(self, value: Any) -> Any:
        """Convert a Firestore value to a Python value."""
        return value


class _KwargsHandler(BaseTypeHandler):
    """Internal handler created from serialize=/deserialize= kwargs."""

    def __init__(
        self,
        serialize_fn: Callable[[Any], Any] | None = None,
        deserialize_fn: Callable[[Any], Any] | None = None,
    ) -> None:
        self._serialize_fn = serialize_fn
        self._deserialize_fn = deserialize_fn

    def serialize(self, value: Any) -> Any:
        if self._serialize_fn is not None:
            return self._serialize_fn(value)
        return value

    def deserialize(self, value: Any) -> Any:
        if self._deserialize_fn is not None:
            return self._deserialize_fn(value)
        return value  # pragma: no cover


class TypeRegistry:
    """Registry of Firestore-compatible types for Field[T] validation and handling."""

    def __init__(self) -> None:
        self._scalar_types: set[type] = set(_SCALAR_TYPES)
        self._checkers: list[Callable[[type], bool]] = []
        self._exact_handlers: dict[type, TypeHandler] = {}
        self._predicate_handlers: list[tuple[Callable[[type], bool], TypeHandler]] = []

    def register(
        self,
        type_or_predicate: type | Callable[[type], bool],
        *,
        handler: TypeHandler | None = None,
        serialize: Callable[[Any], Any] | None = None,
        deserialize: Callable[[Any], Any] | None = None,
    ) -> None:
        """Register a type or predicate with an optional handler.

        Args:
            type_or_predicate: A type (exact match) or callable (predicate).
            handler: A TypeHandler instance. Mutually exclusive with kwargs.
            serialize: Serialize function. Requires deserialize.
            deserialize: Deserialize function.

        Raises:
            ValueError: If handler and kwargs are both provided, or serialize
                        without deserialize.
        """
        if handler is not None and (serialize is not None or deserialize is not None):
            raise ValueError("handler= and serialize=/deserialize= are mutually exclusive")
        if serialize is not None and deserialize is None:
            raise ValueError(
                "serialize= requires deserialize= (cannot serialize without deserialize)"
            )

        if handler is None and (serialize is not None or deserialize is not None):
            handler = _KwargsHandler(serialize_fn=serialize, deserialize_fn=deserialize)

        if isinstance(type_or_predicate, type):
            self._scalar_types.add(type_or_predicate)
            if handler is not None:
                self._exact_handlers[type_or_predicate] = handler
        else:
            self._checkers.append(type_or_predicate)
            if handler is not None:
                self._predicate_handlers.append((type_or_predicate, handler))

    def get_handler(self, hint: type) -> TypeHandler | None:
        """Look up the handler for a type.

        Returns None for built-in types (handled internally).

        Lookup order:
            1. Exact type match
            2. First matching predicate (registration order)
            3. None
        """
        if hint in self._exact_handlers:
            return self._exact_handlers[hint]
        for predicate, handler in self._predicate_handlers:
            try:
                if predicate(hint):
                    return handler
            except TypeError:
                continue
        return None

    def validate(self, field_name: str, hint: Any, class_name: str) -> None:
        """Validate a type hint is Firestore-compatible.

        Args:
            field_name: Name of the field being validated.
            hint: The type hint to validate.
            class_name: Name of the class for error messages.

        Raises:
            TypeError: If the type is not Firestore-compatible.
        """
        self._validate_hint(hint, field_name, class_name, context="")

    def _validate_hint(self, hint: Any, field_name: str, class_name: str, context: str) -> None:
        # Scalar types (includes user-registered types)
        if isinstance(hint, type) and hint in self._scalar_types:
            return

        # Bare container types (list, dict, etc. without parameters)
        if isinstance(hint, type) and hint in _CONTAINER_TYPES:
            return

        origin = get_origin(hint)
        args = get_args(hint)

        # Optional: T | None
        if isinstance(hint, types.UnionType):
            non_none = [a for a in args if a is not type(None)]
            for arg in non_none:
                self._validate_hint(arg, field_name, class_name, context)
            return

        # Containers: list[T], set[T], tuple[T1, T2], dict[K, V]
        if origin in _CONTAINER_TYPES:
            if origin is dict and args:
                key_type = args[0]
                if key_type is not str:
                    key_name = key_type.__name__ if isinstance(key_type, type) else str(key_type)
                    raise TypeError(
                        f"Field '{field_name}' on '{class_name}': "
                        f"dict keys must be str, got {key_name}"
                        f"{f' in {context}' if context else ''}."
                    )
                if len(args) > 1:
                    self._validate_hint(args[1], field_name, class_name, "dict[str, ...]")
            elif args:
                container_name = origin.__name__
                for arg in args:
                    self._validate_hint(arg, field_name, class_name, f"{container_name}[...]")
            return

        # Enum types
        if isinstance(hint, type) and issubclass(hint, enum.Enum):
            return

        # Structured types
        if isinstance(hint, type):
            from .model import Map, Model

            if issubclass(hint, Model):
                raise TypeError(
                    f"Field '{field_name}' on '{class_name}': "
                    f"cannot nest Model '{hint.__name__}'. "
                    f"Use Map for embedded data."
                )
            if issubclass(hint, Map):
                return
            if dataclasses.is_dataclass(hint):
                return
            if is_typeddict(hint):
                return

            # Custom checkers
            for checker in self._checkers:
                try:
                    if checker(hint):
                        return
                except TypeError:
                    continue

        type_name = hint.__name__ if isinstance(hint, type) else str(hint)
        raise TypeError(
            f"Field '{field_name}' on '{class_name}': unsupported type "
            f"'{type_name}'"
            f"{f' in {context}' if context else ''}. "
            f"Firestore does not support this type."
        )


# Global default registry
default_registry = TypeRegistry()

# Third-party structured type detection
try:
    from pydantic import BaseModel as PydanticBaseModel  # type: ignore[import-not-found]

    default_registry.register(lambda cls: issubclass(cls, PydanticBaseModel))  # pragma: no cover
except ImportError:
    pass

try:
    import attrs  # type: ignore[import-not-found]

    default_registry.register(lambda cls: attrs.has(cls))  # pragma: no cover
except ImportError:
    pass

try:
    from msgspec import Struct as MsgspecStruct  # type: ignore[import-not-found]

    default_registry.register(lambda cls: issubclass(cls, MsgspecStruct))  # pragma: no cover
except ImportError:
    pass


def register_type(
    type_or_predicate: type | Callable[[type], bool],
    *,
    handler: TypeHandler | None = None,
    serialize: Callable[[Any], Any] | None = None,
    deserialize: Callable[[Any], Any] | None = None,
) -> None:
    """Register a type handler in the global registry.

    Args:
        type_or_predicate: A type (exact match) or callable (predicate).
        handler: A TypeHandler instance. Mutually exclusive with kwargs.
        serialize: Serialize function. Requires deserialize.
        deserialize: Deserialize function.
    """
    default_registry.register(
        type_or_predicate,
        handler=handler,
        serialize=serialize,
        deserialize=deserialize,
    )
