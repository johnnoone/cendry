from __future__ import annotations

from google.cloud.firestore_v1.base_query import FieldFilter as FieldFilter

from cendry.exceptions import CendryError


class Filter:
    """Base class for composable filters."""

    def __and__(self, other: Filter | FieldFilter) -> And:
        return And(self, other)

    def __or__(self, other: Filter | FieldFilter) -> Or:
        return Or(self, other)


class And(Filter):
    """Composite AND filter."""

    def __init__(self, *filters: Filter | FieldFilter) -> None:
        if len(filters) < 2:
            raise CendryError("And requires at least 2 filters")
        self.filters = filters


class Or(Filter):
    """Composite OR filter."""

    def __init__(self, *filters: Filter | FieldFilter) -> None:
        if len(filters) < 2:
            raise CendryError("Or requires at least 2 filters")
        self.filters = filters
