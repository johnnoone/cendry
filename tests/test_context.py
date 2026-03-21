from unittest.mock import MagicMock

import pytest

from unittest.mock import AsyncMock

from cendry import AsyncCendry, Cendry, DocumentNotFound, Field, FieldFilter, Model
from tests.conftest import City, Mayor, Neighborhood, make_mock_document


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


# --- Nested Map deserialization ---


def test_get_with_nested_map(mock_firestore_client: MagicMock):
    doc = make_mock_document("SF", {
        "name": "San Francisco",
        "state": "CA",
        "country": "USA",
        "capital": False,
        "population": 870000,
        "regions": ["west_coast"],
        "mayor": {"name": "London Breed", "since": 2018},
    })
    mock_firestore_client.collection.return_value.document.return_value.get.return_value = doc

    ctx = Cendry(client=mock_firestore_client)
    city = ctx.get(City, "SF")

    assert isinstance(city.mayor, Mayor)
    assert city.mayor.name == "London Breed"
    assert city.mayor.since == 2018


def test_get_with_null_nested_map(mock_firestore_client: MagicMock):
    doc = make_mock_document("SF", {
        "name": "San Francisco",
        "state": "CA",
        "country": "USA",
        "capital": False,
        "population": 870000,
        "regions": ["west_coast"],
    })
    mock_firestore_client.collection.return_value.document.return_value.get.return_value = doc

    ctx = Cendry(client=mock_firestore_client)
    city = ctx.get(City, "SF")

    assert city.mayor is None


# --- Ordering ---


def test_select_with_order_by(mock_firestore_client: MagicMock):
    from cendry import Asc, Desc

    docs = [
        make_mock_document("SF", {
            "name": "San Francisco", "state": "CA", "country": "USA",
            "capital": False, "population": 870000, "regions": ["west_coast"],
        }),
    ]
    order_mock = MagicMock()
    order_mock.stream.return_value = iter(docs)
    mock_firestore_client.collection.return_value.order_by.return_value = order_mock

    ctx = Cendry(client=mock_firestore_client)
    cities = list(ctx.select(City, order_by=[Asc("population")]))

    assert len(cities) == 1
    mock_firestore_client.collection.return_value.order_by.assert_called_once_with(
        "population", direction="ASCENDING"
    )


# --- Cursors ---


def test_select_with_cursor_dict(mock_firestore_client: MagicMock):
    docs = [
        make_mock_document("SF", {
            "name": "San Francisco", "state": "CA", "country": "USA",
            "capital": False, "population": 870000, "regions": ["west_coast"],
        }),
    ]
    cursor_mock = MagicMock()
    cursor_mock.stream.return_value = iter(docs)
    mock_firestore_client.collection.return_value.start_after.return_value = cursor_mock

    ctx = Cendry(client=mock_firestore_client)
    cities = list(ctx.select(City, start_after={"population": 500000}))

    assert len(cities) == 1
    mock_firestore_client.collection.return_value.start_after.assert_called_once_with(
        {"population": 500000}
    )


def test_select_with_cursor_model(mock_firestore_client: MagicMock):
    city_cursor = City(name="LA", state="CA", country="USA",
                       capital=False, population=3900000, regions=[], id="LA")
    docs = [
        make_mock_document("SF", {
            "name": "San Francisco", "state": "CA", "country": "USA",
            "capital": False, "population": 870000, "regions": ["west_coast"],
        }),
    ]
    cursor_mock = MagicMock()
    cursor_mock.stream.return_value = iter(docs)
    mock_firestore_client.collection.return_value.start_at.return_value = cursor_mock

    ctx = Cendry(client=mock_firestore_client)
    cities = list(ctx.select(City, start_at=city_cursor))

    assert len(cities) == 1
    call_args = mock_firestore_client.collection.return_value.start_at.call_args
    cursor_dict = call_args[0][0]
    assert "id" not in cursor_dict
    assert cursor_dict["name"] == "LA"


def test_select_with_end_cursors(mock_firestore_client: MagicMock):
    docs = []
    end_mock = MagicMock()
    end_mock2 = MagicMock()
    end_mock2.stream.return_value = iter(docs)
    end_mock.end_before.return_value = end_mock2
    mock_firestore_client.collection.return_value.end_at.return_value = end_mock

    ctx = Cendry(client=mock_firestore_client)
    cities = list(ctx.select(City, end_at={"population": 1000000}, end_before={"population": 2000000}))

    assert len(cities) == 0


# --- Composite filters through select ---


def test_select_with_and_filter(mock_firestore_client: MagicMock):
    from cendry import And

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
    cities = list(ctx.select(City, And(City.state.eq("CA"), City.population.gt(500000))))

    assert len(cities) == 1


def test_select_with_or_filter(mock_firestore_client: MagicMock):
    from cendry import Or

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
    cities = list(ctx.select(City, Or(City.state.eq("CA"), City.state.eq("NY"))))

    assert len(cities) == 1


def test_select_with_nested_composite(mock_firestore_client: MagicMock):
    from cendry import And, Or

    docs = []
    query_mock = MagicMock()
    query_mock.stream.return_value = iter(docs)
    mock_firestore_client.collection.return_value.where.return_value = query_mock

    ctx = Cendry(client=mock_firestore_client)
    cities = list(ctx.select(
        City,
        Or(
            City.state.eq("CA"),
            And(City.country.eq("Japan"), City.population.gt(1000000)),
        ),
    ))

    assert len(cities) == 0


# --- Error cases ---


def test_select_unknown_filter_raises(mock_firestore_client: MagicMock):
    from cendry import CendryError

    ctx = Cendry(client=mock_firestore_client)
    with pytest.raises(CendryError, match="Unknown filter type"):
        list(ctx.select(City, "not_a_filter"))


# --- AsyncCendry with filters ---


def test_select_with_raw_fieldfilter_in_or(mock_firestore_client: MagicMock):
    """Cover _to_firestore_filter for FsFieldFilter and Or branches."""
    from cendry import Or

    docs = []
    query_mock = MagicMock()
    query_mock.stream.return_value = iter(docs)
    mock_firestore_client.collection.return_value.where.return_value = query_mock

    ctx = Cendry(client=mock_firestore_client)
    # Use raw FieldFilter inside Or to cover _to_firestore_filter FsFieldFilter branch
    list(ctx.select(
        City,
        Or(FieldFilter("state", "==", "CA"), FieldFilter("state", "==", "NY")),
    ))


def test_nested_map_in_map_deserialization(mock_firestore_client: MagicMock):
    """Cover _deserialize_map recursive branch."""
    from cendry import Map as CendryMap

    class Address(CendryMap):
        street: Field[str]

    class Person(CendryMap):
        name: Field[str]
        address: Field[Address]

    class Company(Model, collection="companies"):
        name: Field[str]
        ceo: Field[Person]

    doc = make_mock_document("ACME", {
        "name": "Acme Corp",
        "ceo": {
            "name": "Jane",
            "address": {"street": "123 Main"},
        },
    })
    mock_firestore_client.collection.return_value.document.return_value.get.return_value = doc

    ctx = Cendry(client=mock_firestore_client)
    company = ctx.get(Company, "ACME")

    assert company.ceo.name == "Jane"
    assert company.ceo.address.street == "123 Main"


def test_field_with_default_factory():
    """Cover field(default_factory=...) branch."""
    from cendry import field as cendry_field

    class Item(Model, collection="items"):
        name: Field[str]
        tags: Field[list[str]] = cendry_field(default_factory=list)

    item = Item(name="test")
    assert item.tags == []


def test_to_firestore_filter_or_branch(mock_firestore_client: MagicMock):
    """Cover _to_firestore_filter Or conversion inside And."""
    from cendry import And, Or

    docs = []
    query_mock = MagicMock()
    query_mock.stream.return_value = iter(docs)
    mock_firestore_client.collection.return_value.where.return_value = query_mock

    ctx = Cendry(client=mock_firestore_client)
    # And containing Or triggers _to_firestore_filter for Or
    list(ctx.select(
        City,
        And(
            City.state.eq("CA"),
            Or(City.country.eq("USA"), City.country.eq("Japan")),
        ),
    ))


def test_resolve_map_type_non_map():
    """Cover _resolve_map_type returning None for non-Map type."""
    from cendry.context import _BaseCendry

    base = _BaseCendry()
    assert base._resolve_map_type(str) is None
    assert base._resolve_map_type("some_string") is None
    assert base._resolve_map_type(None) is None


def test_async_cendry_default_client():
    """Cover AsyncCendry default client creation."""
    from unittest.mock import patch

    with patch("google.cloud.firestore.AsyncClient") as mock_client:
        ctx = AsyncCendry()
        mock_client.assert_called_once()
        assert ctx._client is mock_client.return_value


@pytest.mark.anyio
async def test_async_select_with_filter(mock_firestore_client: MagicMock):
    docs = [
        make_mock_document("SF", {
            "name": "San Francisco", "state": "CA", "country": "USA",
            "capital": False, "population": 870000, "regions": ["west_coast"],
        }),
    ]

    async def mock_stream():
        for d in docs:
            yield d

    query_mock = MagicMock()
    query_mock.stream = mock_stream
    mock_firestore_client.collection.return_value.where.return_value = query_mock

    ctx = AsyncCendry(client=mock_firestore_client)
    cities = []
    async for city in ctx.select(City, City.state.eq("CA")):
        cities.append(city)

    assert len(cities) == 1
