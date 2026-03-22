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


def test_query_select_calls_firestore_select():
    mock_query = MagicMock()
    q = Query(mock_query, City, lambda q, f: q)
    q.select("name", "state")
    mock_query.select.assert_called_once_with(["name", "state"])


def test_query_select_with_field_descriptor():
    mock_query = MagicMock()
    q = Query(mock_query, City, lambda q, f: q)
    q.select(City.name, City.state)
    mock_query.select.assert_called_once_with(["name", "state"])


def test_query_select_preserves_registry():
    custom = TypeRegistry()
    mock_query = MagicMock()
    q = Query(mock_query, City, lambda q, f: q, registry=custom)
    projected = q.select("name")
    assert projected._registry is custom


def test_async_query_select():
    mock_query = MagicMock()
    q = AsyncQuery(mock_query, City, lambda q, f: q)
    q.select("name")
    mock_query.select.assert_called_once_with(["name"])


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
