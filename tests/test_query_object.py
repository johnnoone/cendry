from unittest.mock import AsyncMock, MagicMock

import pytest

from cendry import AsyncCendry, Cendry, CendryError, DocumentNotFoundError
from cendry.query import AsyncQuery, Query
from tests.conftest import City, Neighborhood, make_mock_document

SF_DATA = {
    "name": "San Francisco",
    "state": "CA",
    "country": "USA",
    "capital": False,
    "population": 870_000,
    "regions": ["west_coast"],
}


def _mock_stream(docs):
    mock = MagicMock()
    mock.stream.return_value = iter(docs)
    return mock


# --- Query type ---


def test_select_returns_query(mock_firestore_client: MagicMock):
    mock_firestore_client.collection.return_value.stream.return_value = iter([])
    ctx = Cendry(client=mock_firestore_client)
    assert isinstance(ctx.select(City), Query)


def test_select_group_returns_query(mock_firestore_client: MagicMock):
    mock_firestore_client.collection_group.return_value.stream.return_value = iter([])
    ctx = Cendry(client=mock_firestore_client)
    assert isinstance(ctx.select_group(Neighborhood), Query)


# --- to_list ---


def test_query_to_list(mock_firestore_client: MagicMock):
    docs = [make_mock_document("SF", SF_DATA)]
    mock_firestore_client.collection.return_value.stream.return_value = iter(docs)
    ctx = Cendry(client=mock_firestore_client)
    cities = ctx.select(City).to_list()
    assert len(cities) == 1
    assert cities[0].name == "San Francisco"


# --- first ---


def test_query_first(mock_firestore_client: MagicMock):
    docs = [make_mock_document("SF", SF_DATA)]
    limit_mock = _mock_stream(docs)
    mock_firestore_client.collection.return_value.limit.return_value = limit_mock
    ctx = Cendry(client=mock_firestore_client)
    city = ctx.select(City).first()
    assert city is not None
    assert city.name == "San Francisco"


def test_query_first_empty(mock_firestore_client: MagicMock):
    limit_mock = _mock_stream([])
    mock_firestore_client.collection.return_value.limit.return_value = limit_mock
    ctx = Cendry(client=mock_firestore_client)
    assert ctx.select(City).first() is None


# --- one ---


def test_query_one(mock_firestore_client: MagicMock):
    docs = [make_mock_document("SF", SF_DATA)]
    limit_mock = _mock_stream(docs)
    mock_firestore_client.collection.return_value.limit.return_value = limit_mock
    ctx = Cendry(client=mock_firestore_client)
    city = ctx.select(City).one()
    assert city.name == "San Francisco"


def test_query_one_empty(mock_firestore_client: MagicMock):
    limit_mock = _mock_stream([])
    mock_firestore_client.collection.return_value.limit.return_value = limit_mock
    ctx = Cendry(client=mock_firestore_client)
    with pytest.raises(DocumentNotFoundError):
        ctx.select(City).one()


def test_query_one_multiple(mock_firestore_client: MagicMock):
    docs = [make_mock_document("SF", SF_DATA), make_mock_document("LA", SF_DATA)]
    limit_mock = _mock_stream(docs)
    mock_firestore_client.collection.return_value.limit.return_value = limit_mock
    ctx = Cendry(client=mock_firestore_client)
    with pytest.raises(CendryError, match="more than one"):
        ctx.select(City).one()


# --- exists ---


def test_query_exists_true(mock_firestore_client: MagicMock):
    docs = [make_mock_document("SF", SF_DATA)]
    limit_mock = _mock_stream(docs)
    mock_firestore_client.collection.return_value.limit.return_value = limit_mock
    ctx = Cendry(client=mock_firestore_client)
    assert ctx.select(City).exists() is True


def test_query_exists_false(mock_firestore_client: MagicMock):
    limit_mock = _mock_stream([])
    mock_firestore_client.collection.return_value.limit.return_value = limit_mock
    ctx = Cendry(client=mock_firestore_client)
    assert ctx.select(City).exists() is False


# --- count ---


def test_query_count(mock_firestore_client: MagicMock):
    count_mock = MagicMock()
    count_mock.get.return_value = [[MagicMock(value=42)]]
    mock_firestore_client.collection.return_value.count.return_value = count_mock
    ctx = Cendry(client=mock_firestore_client)
    assert ctx.select(City).count() == 42


# --- filter ---


def test_query_filter(mock_firestore_client: MagicMock):
    docs = [make_mock_document("SF", SF_DATA)]
    where_mock = _mock_stream(docs)
    mock_firestore_client.collection.return_value.where.return_value = where_mock
    ctx = Cendry(client=mock_firestore_client)
    cities = ctx.select(City).filter(City.state.eq("CA")).to_list()
    assert len(cities) == 1


def test_query_filter_list(mock_firestore_client: MagicMock):
    docs = [make_mock_document("SF", SF_DATA)]
    where_mock = MagicMock()
    where_mock.where.return_value = _mock_stream(docs)
    mock_firestore_client.collection.return_value.where.return_value = where_mock
    ctx = Cendry(client=mock_firestore_client)
    cities = ctx.select(City).filter([City.state.eq("CA"), City.population.gt(100)]).to_list()
    assert len(cities) == 1


def test_query_filter_immutable(mock_firestore_client: MagicMock):
    mock_firestore_client.collection.return_value.stream.return_value = iter([])
    where_mock = MagicMock()
    where_mock.stream.return_value = iter([])
    mock_firestore_client.collection.return_value.where.return_value = where_mock
    ctx = Cendry(client=mock_firestore_client)
    q1 = ctx.select(City)
    q2 = q1.filter(City.state.eq("CA"))
    assert q1 is not q2


# --- Async ---


@pytest.mark.anyio
async def test_async_select_returns_async_query(mock_firestore_client: MagicMock):
    ctx = AsyncCendry(client=mock_firestore_client)
    assert isinstance(ctx.select(City), AsyncQuery)


@pytest.mark.anyio
async def test_async_query_to_list(mock_firestore_client: MagicMock):
    docs = [make_mock_document("SF", SF_DATA)]

    async def mock_stream():
        for d in docs:
            yield d

    mock_firestore_client.collection.return_value.stream = mock_stream
    ctx = AsyncCendry(client=mock_firestore_client)
    cities = await ctx.select(City).to_list()
    assert len(cities) == 1


@pytest.mark.anyio
async def test_async_query_first(mock_firestore_client: MagicMock):
    docs = [make_mock_document("SF", SF_DATA)]

    async def mock_stream():
        for d in docs:
            yield d

    limit_mock = MagicMock()
    limit_mock.stream = mock_stream
    mock_firestore_client.collection.return_value.limit.return_value = limit_mock
    ctx = AsyncCendry(client=mock_firestore_client)
    city = await ctx.select(City).first()
    assert city is not None
    assert city.name == "San Francisco"


@pytest.mark.anyio
async def test_async_query_exists(mock_firestore_client: MagicMock):
    docs = [make_mock_document("SF", SF_DATA)]

    async def mock_stream():
        for d in docs:
            yield d

    limit_mock = MagicMock()
    limit_mock.stream = mock_stream
    mock_firestore_client.collection.return_value.limit.return_value = limit_mock
    ctx = AsyncCendry(client=mock_firestore_client)
    assert await ctx.select(City).exists() is True


@pytest.mark.anyio
async def test_async_query_one(mock_firestore_client: MagicMock):
    docs = [make_mock_document("SF", SF_DATA)]

    async def mock_stream():
        for d in docs:
            yield d

    limit_mock = MagicMock()
    limit_mock.stream = mock_stream
    mock_firestore_client.collection.return_value.limit.return_value = limit_mock
    ctx = AsyncCendry(client=mock_firestore_client)
    city = await ctx.select(City).one()
    assert city.name == "San Francisco"


@pytest.mark.anyio
async def test_async_query_count(mock_firestore_client: MagicMock):
    count_mock = MagicMock()
    count_mock.get = AsyncMock(return_value=[[MagicMock(value=7)]])
    mock_firestore_client.collection.return_value.count.return_value = count_mock
    ctx = AsyncCendry(client=mock_firestore_client)
    assert await ctx.select(City).count() == 7


@pytest.mark.anyio
async def test_async_query_filter(mock_firestore_client: MagicMock):
    docs = [make_mock_document("SF", SF_DATA)]

    async def mock_stream():
        for d in docs:
            yield d

    where_mock = MagicMock()
    where_mock.stream = mock_stream
    mock_firestore_client.collection.return_value.where.return_value = where_mock
    ctx = AsyncCendry(client=mock_firestore_client)
    cities = await ctx.select(City).filter(City.state.eq("CA")).to_list()
    assert len(cities) == 1


@pytest.mark.anyio
async def test_async_query_filter_list(mock_firestore_client: MagicMock):
    docs = [make_mock_document("SF", SF_DATA)]

    async def mock_stream():
        for d in docs:
            yield d

    where_mock2 = MagicMock()
    where_mock2.stream = mock_stream
    where_mock = MagicMock()
    where_mock.where.return_value = where_mock2
    mock_firestore_client.collection.return_value.where.return_value = where_mock
    ctx = AsyncCendry(client=mock_firestore_client)
    query = ctx.select(City).filter([City.state.eq("CA"), City.population.gt(100)])
    cities = await query.to_list()
    assert len(cities) == 1


@pytest.mark.anyio
async def test_async_query_first_empty(mock_firestore_client: MagicMock):
    async def mock_stream():
        return
        yield

    limit_mock = MagicMock()
    limit_mock.stream = mock_stream
    mock_firestore_client.collection.return_value.limit.return_value = limit_mock
    ctx = AsyncCendry(client=mock_firestore_client)
    assert await ctx.select(City).first() is None


@pytest.mark.anyio
async def test_async_query_one_empty(mock_firestore_client: MagicMock):
    async def mock_stream():
        return
        yield

    limit_mock = MagicMock()
    limit_mock.stream = mock_stream
    mock_firestore_client.collection.return_value.limit.return_value = limit_mock
    ctx = AsyncCendry(client=mock_firestore_client)
    with pytest.raises(DocumentNotFoundError):
        await ctx.select(City).one()


@pytest.mark.anyio
async def test_async_query_one_multiple(mock_firestore_client: MagicMock):
    docs = [make_mock_document("SF", SF_DATA), make_mock_document("LA", SF_DATA)]

    async def mock_stream():
        for d in docs:
            yield d

    limit_mock = MagicMock()
    limit_mock.stream = mock_stream
    mock_firestore_client.collection.return_value.limit.return_value = limit_mock
    ctx = AsyncCendry(client=mock_firestore_client)
    with pytest.raises(CendryError, match="more than one"):
        await ctx.select(City).one()
