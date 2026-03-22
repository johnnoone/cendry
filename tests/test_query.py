from unittest.mock import MagicMock

import pytest

from cendry import Asc, AsyncQuery, Desc, Field, Model, Query
from cendry.types import TypeRegistry
from tests.conftest import SF_DATA, City, make_mock_document


def test_asc_with_string():
    a = Asc("population")
    assert a.field == "population"
    assert a.direction == "ASCENDING"


def test_desc_with_string():
    d = Desc("population")
    assert d.field == "population"
    assert d.direction == "DESCENDING"


def test_asc_with_field_descriptor():
    class City(Model, collection="cities"):
        population: Field[int]

    a = Asc(City.population)
    assert isinstance(a.field, str)
    assert a.field == "population"
    assert a.direction == "ASCENDING"


def test_desc_with_field_descriptor():
    class City(Model, collection="cities"):
        population: Field[int]

    d = Desc(City.population)
    assert isinstance(d.field, str)
    assert d.field == "population"
    assert d.direction == "DESCENDING"


# --- Registry threading tests ---


def test_query_passes_registry_to_deserialize():
    custom = TypeRegistry()
    docs = [make_mock_document("SF", SF_DATA)]
    mock_query = MagicMock()
    mock_query.stream.return_value = iter(docs)

    q = Query(mock_query, City, lambda q, f: q, registry=custom)
    results = list(q)

    assert len(results) == 1
    assert results[0].name == "San Francisco"


def test_query_filter_preserves_registry():
    custom = TypeRegistry()
    mock_query = MagicMock()
    q = Query(mock_query, City, lambda q, f: q, registry=custom)
    filtered = q.filter()
    assert filtered._registry is custom


def test_query_order_by_preserves_registry():
    custom = TypeRegistry()
    mock_query = MagicMock()
    q = Query(mock_query, City, lambda q, f: q, registry=custom)
    ordered = q.order_by(Asc("name"))
    assert ordered._registry is custom


def test_query_limit_preserves_registry():
    custom = TypeRegistry()
    mock_query = MagicMock()
    q = Query(mock_query, City, lambda q, f: q, registry=custom)
    limited = q.limit(10)
    assert limited._registry is custom


def test_query_first_preserves_registry():
    custom = TypeRegistry()
    docs = [make_mock_document("SF", SF_DATA)]
    mock_query = MagicMock()
    mock_query.limit.return_value = mock_query
    mock_query.stream.return_value = iter(docs)

    q = Query(mock_query, City, lambda q, f: q, registry=custom)
    result = q.first()
    assert result is not None
    assert result.name == "San Francisco"


def test_query_one_preserves_registry():
    custom = TypeRegistry()
    docs = [make_mock_document("SF", SF_DATA)]
    mock_query = MagicMock()
    mock_query.limit.return_value = mock_query
    mock_query.stream.return_value = iter(docs)

    q = Query(mock_query, City, lambda q, f: q, registry=custom)
    result = q.one()
    assert result.name == "San Francisco"


def test_query_chain_preserves_registry():
    custom = TypeRegistry()
    mock_query = MagicMock()
    q = Query(mock_query, City, lambda q, f: q, registry=custom)
    chained = q.filter().limit(10)
    assert chained._registry is custom


def test_async_query_filter_preserves_registry():
    custom = TypeRegistry()
    mock_query = MagicMock()
    q = AsyncQuery(mock_query, City, lambda q, f: q, registry=custom)
    filtered = q.filter()
    assert filtered._registry is custom


def test_async_query_limit_preserves_registry():
    custom = TypeRegistry()
    mock_query = MagicMock()
    q = AsyncQuery(mock_query, City, lambda q, f: q, registry=custom)
    limited = q.limit(10)
    assert limited._registry is custom


@pytest.mark.anyio
async def test_async_query_first_preserves_registry():
    custom = TypeRegistry()
    docs = [make_mock_document("SF", SF_DATA)]
    mock_query = MagicMock()
    mock_query.limit.return_value = mock_query

    async def mock_stream():
        for d in docs:
            yield d

    mock_query.stream = mock_stream

    q = AsyncQuery(mock_query, City, lambda q, f: q, registry=custom)
    result = await q.first()
    assert result is not None
    assert result.name == "San Francisco"


@pytest.mark.anyio
async def test_async_query_iteration_uses_registry():
    custom = TypeRegistry()
    docs = [make_mock_document("SF", SF_DATA)]
    mock_query = MagicMock()

    async def mock_stream():
        for d in docs:
            yield d

    mock_query.stream = mock_stream

    q = AsyncQuery(mock_query, City, lambda q, f: q, registry=custom)
    results = [item async for item in q]
    assert len(results) == 1
    assert results[0].name == "San Francisco"


# --- Projection queries ---


def test_query_project_calls_firestore_select():
    mock_query = MagicMock()
    q = Query(mock_query, City, lambda q, f: q)
    q.project("name", "state")
    mock_query.select.assert_called_once_with(["name", "state"])


def test_query_project_with_field_descriptor():
    mock_query = MagicMock()
    q = Query(mock_query, City, lambda q, f: q)
    q.project(City.name, City.state)
    mock_query.select.assert_called_once_with(["name", "state"])


def test_query_project_returns_projected_query():
    from cendry.query import ProjectedQuery

    mock_query = MagicMock()
    q = Query(mock_query, City, lambda q, f: q)
    result = q.project("name")
    assert isinstance(result, ProjectedQuery)


def test_projected_query_iterates_dicts():
    from cendry.query import ProjectedQuery

    docs = [make_mock_document("SF", {"name": "San Francisco"})]
    mock_query = MagicMock()
    mock_query.stream.return_value = iter(docs)

    pq = ProjectedQuery(mock_query)
    results = list(pq)
    assert len(results) == 1
    assert results[0]["name"] == "San Francisco"
    assert results[0]["id"] == "SF"


def test_async_query_project():
    from cendry.query import AsyncProjectedQuery

    mock_query = MagicMock()
    q = AsyncQuery(mock_query, City, lambda q, f: q)
    result = q.project("name")
    assert isinstance(result, AsyncProjectedQuery)


def test_projected_query_to_list():
    from cendry.query import ProjectedQuery

    docs = [
        make_mock_document("SF", {"name": "SF"}),
        make_mock_document("LA", {"name": "LA"}),
    ]
    mock_query = MagicMock()
    mock_query.stream.return_value = iter(docs)

    pq = ProjectedQuery(mock_query)
    results = pq.to_list()
    assert len(results) == 2
    assert results[0]["id"] == "SF"


def test_projected_query_first():
    from cendry.query import ProjectedQuery

    docs = [make_mock_document("SF", {"name": "SF"})]
    mock_query = MagicMock()
    mock_query.limit.return_value = mock_query
    mock_query.stream.return_value = iter(docs)

    pq = ProjectedQuery(mock_query)
    result = pq.first()
    assert result is not None
    assert result["name"] == "SF"


def test_projected_query_first_empty():
    from cendry.query import ProjectedQuery

    mock_query = MagicMock()
    mock_query.limit.return_value = mock_query
    mock_query.stream.return_value = iter([])

    pq = ProjectedQuery(mock_query)
    assert pq.first() is None


@pytest.mark.anyio
async def test_async_projected_query_iterates():
    from cendry.query import AsyncProjectedQuery

    docs = [make_mock_document("SF", {"name": "SF"})]
    mock_query = MagicMock()

    async def mock_stream():
        for d in docs:
            yield d

    mock_query.stream = mock_stream

    pq = AsyncProjectedQuery(mock_query)
    results = [item async for item in pq]
    assert len(results) == 1
    assert results[0]["name"] == "SF"
    assert results[0]["id"] == "SF"


@pytest.mark.anyio
async def test_async_projected_query_to_list():
    from cendry.query import AsyncProjectedQuery

    docs = [make_mock_document("SF", {"name": "SF"})]
    mock_query = MagicMock()

    async def mock_stream():
        for d in docs:
            yield d

    mock_query.stream = mock_stream

    pq = AsyncProjectedQuery(mock_query)
    results = await pq.to_list()
    assert len(results) == 1


@pytest.mark.anyio
async def test_async_projected_query_first():
    from cendry.query import AsyncProjectedQuery

    docs = [make_mock_document("SF", {"name": "SF"})]
    mock_query = MagicMock()
    mock_query.limit.return_value = mock_query

    async def mock_stream():
        for d in docs:
            yield d

    mock_query.stream = mock_stream

    pq = AsyncProjectedQuery(mock_query)
    result = await pq.first()
    assert result is not None
    assert result["name"] == "SF"


@pytest.mark.anyio
async def test_async_projected_query_first_empty():
    from cendry.query import AsyncProjectedQuery

    mock_query = MagicMock()
    mock_query.limit.return_value = mock_query

    async def mock_stream():
        return
        yield  # make it an async generator

    mock_query.stream = mock_stream

    pq = AsyncProjectedQuery(mock_query)
    assert await pq.first() is None


# --- on_snapshot ---


def test_query_on_snapshot():
    docs = [make_mock_document("SF", SF_DATA)]
    docs[0].update_time = None
    docs[0].create_time = None

    mock_query = MagicMock()
    q = Query(mock_query, City, lambda q, f: q)

    received = []

    def callback(instances, changes, read_time):
        received.append((instances, changes, read_time))

    q.on_snapshot(callback)

    # Simulate Firestore calling the wrapper
    wrapper = mock_query.on_snapshot.call_args[0][0]
    wrapper(docs, ["change1"], "2026-01-01")

    assert len(received) == 1
    instances, changes, _read_time = received[0]
    assert len(instances) == 1
    assert instances[0].name == "San Francisco"
    assert changes == ["change1"]
