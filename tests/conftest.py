"""Shared test configuration."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from cendry import Field, Map, Model, field


SF_DATA = {
    "name": "San Francisco",
    "state": "CA",
    "country": "USA",
    "capital": False,
    "population": 870000,
    "regions": ["west_coast"],
}


class Mayor(Map):
    name: Field[str]
    since: Field[int]


class City(Model, collection="cities"):
    name: Field[str]
    state: Field[str]
    country: Field[str]
    capital: Field[bool]
    population: Field[int]
    regions: Field[list[str]]
    nickname: Field[str | None] = field(default=None)
    mayor: Field[Mayor | None] = field(default=None)


class Neighborhood(Model, collection="neighborhoods"):
    name: Field[str]
    population: Field[int]


def make_mock_document(
    doc_id: str,
    data: dict[str, Any],
    *,
    exists: bool = True,
) -> MagicMock:
    """Create a mock Firestore DocumentSnapshot."""
    doc = MagicMock()
    doc.id = doc_id
    doc.exists = exists
    doc.to_dict.return_value = data if exists else None
    return doc


@pytest.fixture
def mock_firestore_client() -> MagicMock:
    """Create a mock Firestore Client."""
    return MagicMock()
