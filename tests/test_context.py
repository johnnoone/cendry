from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from unittest.mock import AsyncMock

from cendry import AsyncCendry, Cendry, DocumentNotFound, FieldFilter
from tests.conftest import City, Neighborhood, make_mock_document


# --- get / find ---


def test_get_existing_document(mock_firestore_client: MagicMock):
    doc = make_mock_document("SF", {
        "name": "San Francisco", "state": "CA", "country": "USA",
        "capital": False, "population": 870000, "regions": ["west_coast"],
    })
    mock_firestore_client.collection.return_value.document.return_value.get.return_value = doc

    ctx = Cendry(client=mock_firestore_client)
    city = ctx.get(City, "SF")

    assert city.id == "SF"
    assert city.name == "San Francisco"
    assert city.state == "CA"
    assert isinstance(city, City)


def test_get_nonexistent_document(mock_firestore_client: MagicMock):
    doc = make_mock_document("NOPE", {}, exists=False)
    mock_firestore_client.collection.return_value.document.return_value.get.return_value = doc

    ctx = Cendry(client=mock_firestore_client)
    with pytest.raises(DocumentNotFound):
        ctx.get(City, "NOPE")


def test_find_existing_document(mock_firestore_client: MagicMock):
    doc = make_mock_document("SF", {
        "name": "San Francisco", "state": "CA", "country": "USA",
        "capital": False, "population": 870000, "regions": ["west_coast"],
    })
    mock_firestore_client.collection.return_value.document.return_value.get.return_value = doc

    ctx = Cendry(client=mock_firestore_client)
    city = ctx.find(City, "SF")
    assert city is not None
    assert city.name == "San Francisco"


def test_find_nonexistent_document(mock_firestore_client: MagicMock):
    doc = make_mock_document("NOPE", {}, exists=False)
    mock_firestore_client.collection.return_value.document.return_value.get.return_value = doc

    ctx = Cendry(client=mock_firestore_client)
    result = ctx.find(City, "NOPE")
    assert result is None


# --- select ---


def test_select_with_field_filter(mock_firestore_client: MagicMock):
    docs = [
        make_mock_document("SF", {
            "name": "San Francisco", "state": "CA", "country": "USA",
            "capital": False, "population": 870000, "regions": ["west_coast"],
        }),
        make_mock_document("LA", {
            "name": "Los Angeles", "state": "CA", "country": "USA",
            "capital": False, "population": 3900000, "regions": ["west_coast"],
        }),
    ]
    query_mock = MagicMock()
    query_mock.stream.return_value = iter(docs)
    mock_firestore_client.collection.return_value.where.return_value = query_mock

    ctx = Cendry(client=mock_firestore_client)
    cities = list(ctx.select(City, FieldFilter("state", "==", "CA")))

    assert len(cities) == 2
    assert all(isinstance(c, City) for c in cities)
    assert cities[0].name == "San Francisco"


def test_select_no_filters(mock_firestore_client: MagicMock):
    docs = [
        make_mock_document("SF", {
            "name": "San Francisco", "state": "CA", "country": "USA",
            "capital": False, "population": 870000, "regions": ["west_coast"],
        }),
    ]
    mock_firestore_client.collection.return_value.stream.return_value = iter(docs)

    ctx = Cendry(client=mock_firestore_client)
    cities = list(ctx.select(City))

    assert len(cities) == 1


def test_select_with_limit(mock_firestore_client: MagicMock):
    docs = [
        make_mock_document("SF", {
            "name": "San Francisco", "state": "CA", "country": "USA",
            "capital": False, "population": 870000, "regions": ["west_coast"],
        }),
    ]
    limit_mock = MagicMock()
    limit_mock.stream.return_value = iter(docs)
    mock_firestore_client.collection.return_value.limit.return_value = limit_mock

    ctx = Cendry(client=mock_firestore_client)
    cities = list(ctx.select(City, limit=1))

    assert len(cities) == 1
    mock_firestore_client.collection.return_value.limit.assert_called_once_with(1)


def test_select_with_parent(mock_firestore_client: MagicMock):
    city = City(name="San Francisco", state="CA", country="USA",
                capital=False, population=870000, regions=["west_coast"], id="SF")
    docs = [
        make_mock_document("MISSION", {"name": "Mission", "population": 60000}),
    ]
    parent_doc = mock_firestore_client.collection.return_value.document.return_value
    parent_doc.collection.return_value.stream.return_value = iter(docs)

    ctx = Cendry(client=mock_firestore_client)
    neighborhoods = list(ctx.select(Neighborhood, parent=city))

    assert len(neighborhoods) == 1
    assert neighborhoods[0].name == "Mission"


def test_select_with_field_descriptor_filter(mock_firestore_client: MagicMock):
    docs = [
        make_mock_document("SF", {
            "name": "San Francisco", "state": "CA", "country": "USA",
            "capital": False, "population": 870000, "regions": ["west_coast"],
        }),
    ]
    query_mock = MagicMock()
    query_mock.stream.return_value = iter(docs)
    mock_firestore_client.collection.return_value.where.return_value = query_mock

    ctx = Cendry(client=mock_firestore_client)
    cities = list(ctx.select(City, City.state.eq("CA")))

    assert len(cities) == 1
    assert cities[0].state == "CA"


# --- select_group ---


def test_select_group(mock_firestore_client: MagicMock):
    docs = [
        make_mock_document("MISSION", {"name": "Mission", "population": 60000}),
        make_mock_document("SHIBUYA", {"name": "Shibuya", "population": 230000}),
    ]
    query_mock = MagicMock()
    query_mock.stream.return_value = iter(docs)
    mock_firestore_client.collection_group.return_value = query_mock

    ctx = Cendry(client=mock_firestore_client)
    neighborhoods = list(ctx.select_group(Neighborhood))

    assert len(neighborhoods) == 2
    mock_firestore_client.collection_group.assert_called_once_with("neighborhoods")


# --- parent validation ---


def test_parent_requires_id(mock_firestore_client: MagicMock):
    from cendry import CendryError

    city = City(name="SF", state="CA", country="USA",
                capital=False, population=870000, regions=[])
    # city.id is None

    ctx = Cendry(client=mock_firestore_client)
    with pytest.raises(CendryError, match="non-None id"):
        list(ctx.select(Neighborhood, parent=city))


# --- AsyncCendry tests ---


@pytest.mark.anyio
async def test_async_get_existing(mock_firestore_client: MagicMock):
    doc = make_mock_document("SF", {
        "name": "San Francisco", "state": "CA", "country": "USA",
        "capital": False, "population": 870000, "regions": ["west_coast"],
    })
    mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(return_value=doc)

    ctx = AsyncCendry(client=mock_firestore_client)
    city = await ctx.get(City, "SF")

    assert city.id == "SF"
    assert city.name == "San Francisco"


@pytest.mark.anyio
async def test_async_get_not_found(mock_firestore_client: MagicMock):
    doc = make_mock_document("NOPE", {}, exists=False)
    mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(return_value=doc)

    ctx = AsyncCendry(client=mock_firestore_client)
    with pytest.raises(DocumentNotFound):
        await ctx.get(City, "NOPE")


@pytest.mark.anyio
async def test_async_find_existing(mock_firestore_client: MagicMock):
    doc = make_mock_document("SF", {
        "name": "San Francisco", "state": "CA", "country": "USA",
        "capital": False, "population": 870000, "regions": ["west_coast"],
    })
    mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(return_value=doc)

    ctx = AsyncCendry(client=mock_firestore_client)
    city = await ctx.find(City, "SF")
    assert city is not None
    assert city.name == "San Francisco"


@pytest.mark.anyio
async def test_async_find_not_found(mock_firestore_client: MagicMock):
    doc = make_mock_document("NOPE", {}, exists=False)
    mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(return_value=doc)

    ctx = AsyncCendry(client=mock_firestore_client)
    result = await ctx.find(City, "NOPE")
    assert result is None


@pytest.mark.anyio
async def test_async_select(mock_firestore_client: MagicMock):
    docs = [
        make_mock_document("SF", {
            "name": "San Francisco", "state": "CA", "country": "USA",
            "capital": False, "population": 870000, "regions": ["west_coast"],
        }),
    ]

    async def mock_stream():
        for d in docs:
            yield d

    mock_firestore_client.collection.return_value.stream = mock_stream

    ctx = AsyncCendry(client=mock_firestore_client)
    cities = []
    async for city in ctx.select(City):
        cities.append(city)

    assert len(cities) == 1
    assert cities[0].name == "San Francisco"


@pytest.mark.anyio
async def test_async_select_group(mock_firestore_client: MagicMock):
    docs = [
        make_mock_document("MISSION", {"name": "Mission", "population": 60000}),
    ]

    async def mock_stream():
        for d in docs:
            yield d

    query_mock = MagicMock()
    query_mock.stream = mock_stream
    mock_firestore_client.collection_group.return_value = query_mock

    ctx = AsyncCendry(client=mock_firestore_client)
    neighborhoods = []
    async for n in ctx.select_group(Neighborhood):
        neighborhoods.append(n)

    assert len(neighborhoods) == 1
    assert neighborhoods[0].name == "Mission"
