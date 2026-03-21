import dataclasses
import datetime
import enum
import types
from collections.abc import Callable
from decimal import Decimal
from typing import Any, get_args, get_origin, is_typeddict

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
        GeoPoint,
        DocumentReference,
    }
)

_CONTAINER_TYPES: frozenset[type] = frozenset({list, tuple, set, dict})


class TypeRegistry:
    """Registry of Firestore-compatible types for Field[T] validation."""

    def __init__(self) -> None:
        self._scalar_types: set[type] = set(_SCALAR_TYPES)
        self._checkers: list[Callable[[type], bool]] = []

    def register(self, type_or_predicate: type | Callable[[type], bool]) -> None:
        """Register a type or predicate as Firestore-compatible.

        Args:
            type_or_predicate: A type class, or a callable that takes a type and returns True
                               if it should be accepted.
        """
        if isinstance(type_or_predicate, type):
            self._scalar_types.add(type_or_predicate)
        else:
            self._checkers.append(type_or_predicate)

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
        # Scalar types
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


def register_type(type_or_predicate: type | Callable[[type], bool]) -> None:
    """Register a type or predicate as Firestore-compatible in the global registry."""
    default_registry.register(type_or_predicate)
