import datetime
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from google.cloud.firestore_v1._helpers import GeoPoint
from google.cloud.firestore_v1.document import DocumentReference

_SCALAR_TYPES: frozenset[type] = frozenset({
    str,
    int,
    float,
    bool,
    bytes,
    Decimal,
    datetime.datetime,
    GeoPoint,
    DocumentReference,
})

_CONTAINER_TYPES: frozenset[type] = frozenset({list, tuple, set, dict})


class TypeRegistry:
    """Registry of Firestore-compatible types for Field[T] validation."""

    def __init__(self) -> None:
        self._scalar_types: set[type] = set(_SCALAR_TYPES)
        self._checkers: list[Callable[[type], bool]] = []

    def register(self, type_or_predicate: type | Callable[[type], bool]) -> None:
        """Register a type or predicate as Firestore-compatible."""
        if isinstance(type_or_predicate, type):
            self._scalar_types.add(type_or_predicate)
        else:
            self._checkers.append(type_or_predicate)

    def validate(self, field_name: str, hint: Any, class_name: str) -> None:
        """Validate a type hint is Firestore-compatible. Raises TypeError if not."""
        self._validate_hint(hint, field_name, class_name, context="")

    def _validate_hint(
        self, hint: Any, field_name: str, class_name: str, context: str
    ) -> None:
        # Scalar types
        if isinstance(hint, type) and hint in self._scalar_types:
            return

        type_name = hint.__name__ if isinstance(hint, type) else str(hint)
        raise TypeError(
            f"Field '{field_name}' on '{class_name}': unsupported type "
            f"'{type_name}'"
            f"{f' in {context}' if context else ''}. "
            f"Firestore does not support this type."
        )
