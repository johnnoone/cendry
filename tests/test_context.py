from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import cendry
from cendry import (
    And,
    Asc,
    AsyncCendry,
    Cendry,
    CendryError,
    DocumentAlreadyExistsError,
    DocumentNotFoundError,
    Field,
    FieldFilter,
    Map,
    Model,
    Or,
)
from google.api_core.exceptions import NotFound

from cendry.serialize import to_dict
from cendry.types import BaseTypeHandler, TypeRegistry, default_registry
from tests.conftest import SF_DATA, City, Mayor, Neighborhood, make_mock_document

# --- get / find ---


def test_get_existing_document(mock_firestore_client: MagicMock):
    doc = make_mock_document("SF", SF_DATA)
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
    with pytest.raises(DocumentNotFoundError):
        ctx.get(City, "NOPE")


def test_find_existing_document(mock_firestore_client: MagicMock):
    doc = make_mock_document("SF", SF_DATA)
    mock_firestore_client.collection.return_value.document.return_value.get.return_value = doc

    ctx = Cendry(client=mock_firestore_client)
    city = ctx.find(City, "SF")
    assert city is not None
    assert city.name == "San Francisco"


def test_find_nonexistent_document(mock_firestore_client: MagicMock):
    doc = make_mock_document("NOPE", {}, exists=False)
    mock_firestore_client.collection.return_value.document.return_value.get.return_value = doc

    ctx = Cendry(client=mock_firestore_client)
    assert ctx.find(City, "NOPE") is None


# --- select ---


def test_select_with_field_filter(mock_firestore_client: MagicMock):
    docs = [
        make_mock_document("SF", SF_DATA),
        make_mock_document("LA", {**SF_DATA, "name": "Los Angeles", "population": 3_900_000}),
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
    docs = [make_mock_document("SF", SF_DATA)]
    mock_firestore_client.collection.return_value.stream.return_value = iter(docs)

    ctx = Cendry(client=mock_firestore_client)
    assert len(list(ctx.select(City))) == 1


def test_select_with_limit(mock_firestore_client: MagicMock):
    docs = [make_mock_document("SF", SF_DATA)]
    limit_mock = MagicMock()
    limit_mock.stream.return_value = iter(docs)
    mock_firestore_client.collection.return_value.limit.return_value = limit_mock

    ctx = Cendry(client=mock_firestore_client)
    assert len(list(ctx.select(City, limit=1))) == 1
    mock_firestore_client.collection.return_value.limit.assert_called_once_with(1)


def test_select_with_parent(mock_firestore_client: MagicMock):
    city = City(**SF_DATA, id="SF")
    docs = [make_mock_document("MISSION", {"name": "Mission", "population": 60_000})]
    parent_doc = mock_firestore_client.collection.return_value.document.return_value
    parent_doc.collection.return_value.stream.return_value = iter(docs)

    ctx = Cendry(client=mock_firestore_client)
    neighborhoods = list(ctx.select(Neighborhood, parent=city))

    assert len(neighborhoods) == 1
    assert neighborhoods[0].name == "Mission"


def test_select_with_field_descriptor_filter(mock_firestore_client: MagicMock):
    docs = [make_mock_document("SF", SF_DATA)]
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
        make_mock_document("MISSION", {"name": "Mission", "population": 60_000}),
        make_mock_document("SHIBUYA", {"name": "Shibuya", "population": 230_000}),
    ]
    query_mock = MagicMock()
    query_mock.stream.return_value = iter(docs)
    mock_firestore_client.collection_group.return_value = query_mock

    ctx = Cendry(client=mock_firestore_client)
    assert len(list(ctx.select_group(Neighborhood))) == 2
    mock_firestore_client.collection_group.assert_called_once_with("neighborhoods")


# --- parent validation ---


def test_parent_requires_id(mock_firestore_client: MagicMock):
    city = City(
        name="SF",
        state="CA",
        country="USA",
        capital=False,
        population=870_000,
        regions=[],
    )

    ctx = Cendry(client=mock_firestore_client)
    with pytest.raises(CendryError, match="non-None id"):
        list(ctx.select(Neighborhood, parent=city))


# --- AsyncCendry ---


@pytest.mark.anyio
async def test_async_get_existing(mock_firestore_client: MagicMock):
    doc = make_mock_document("SF", SF_DATA)
    mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
        return_value=doc,
    )

    ctx = AsyncCendry(client=mock_firestore_client)
    city = await ctx.get(City, "SF")

    assert city.id == "SF"
    assert city.name == "San Francisco"


@pytest.mark.anyio
async def test_async_get_not_found(mock_firestore_client: MagicMock):
    doc = make_mock_document("NOPE", {}, exists=False)
    mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
        return_value=doc,
    )

    ctx = AsyncCendry(client=mock_firestore_client)
    with pytest.raises(DocumentNotFoundError):
        await ctx.get(City, "NOPE")


@pytest.mark.anyio
async def test_async_find_existing(mock_firestore_client: MagicMock):
    doc = make_mock_document("SF", SF_DATA)
    mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
        return_value=doc,
    )

    ctx = AsyncCendry(client=mock_firestore_client)
    city = await ctx.find(City, "SF")
    assert city is not None
    assert city.name == "San Francisco"


@pytest.mark.anyio
async def test_async_find_not_found(mock_firestore_client: MagicMock):
    doc = make_mock_document("NOPE", {}, exists=False)
    mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
        return_value=doc,
    )

    ctx = AsyncCendry(client=mock_firestore_client)
    assert await ctx.find(City, "NOPE") is None


@pytest.mark.anyio
async def test_async_select(mock_firestore_client: MagicMock):
    docs = [make_mock_document("SF", SF_DATA)]

    async def mock_stream():
        for d in docs:
            yield d

    mock_firestore_client.collection.return_value.stream = mock_stream

    ctx = AsyncCendry(client=mock_firestore_client)
    cities = [city async for city in ctx.select(City)]

    assert len(cities) == 1
    assert cities[0].name == "San Francisco"


@pytest.mark.anyio
async def test_async_select_group(mock_firestore_client: MagicMock):
    docs = [make_mock_document("MISSION", {"name": "Mission", "population": 60_000})]

    async def mock_stream():
        for d in docs:
            yield d

    query_mock = MagicMock()
    query_mock.stream = mock_stream
    mock_firestore_client.collection_group.return_value = query_mock

    ctx = AsyncCendry(client=mock_firestore_client)
    neighborhoods = [n async for n in ctx.select_group(Neighborhood)]

    assert len(neighborhoods) == 1
    assert neighborhoods[0].name == "Mission"


@pytest.mark.anyio
async def test_async_select_with_filter(mock_firestore_client: MagicMock):
    docs = [make_mock_document("SF", SF_DATA)]

    async def mock_stream():
        for d in docs:
            yield d

    query_mock = MagicMock()
    query_mock.stream = mock_stream
    mock_firestore_client.collection.return_value.where.return_value = query_mock

    ctx = AsyncCendry(client=mock_firestore_client)
    cities = [city async for city in ctx.select(City, City.state.eq("CA"))]

    assert len(cities) == 1


def test_async_cendry_default_client():
    with patch("google.cloud.firestore.AsyncClient") as mock_client:
        ctx = AsyncCendry()
        mock_client.assert_called_once()
        assert ctx._client is mock_client.return_value


# --- Nested Map deserialization ---


def test_get_with_nested_map(mock_firestore_client: MagicMock):
    doc = make_mock_document(
        "SF",
        {
            **SF_DATA,
            "mayor": {"name": "London Breed", "since": 2018},
        },
    )
    mock_firestore_client.collection.return_value.document.return_value.get.return_value = doc

    ctx = Cendry(client=mock_firestore_client)
    city = ctx.get(City, "SF")

    assert isinstance(city.mayor, Mayor)
    assert city.mayor.name == "London Breed"
    assert city.mayor.since == 2018


def test_get_with_null_nested_map(mock_firestore_client: MagicMock):
    doc = make_mock_document("SF", SF_DATA)
    mock_firestore_client.collection.return_value.document.return_value.get.return_value = doc

    ctx = Cendry(client=mock_firestore_client)
    assert ctx.get(City, "SF").mayor is None


def test_nested_map_in_map_deserialization(mock_firestore_client: MagicMock):
    class Address(Map):
        street: Field[str]

    class Person(Map):
        name: Field[str]
        address: Field[Address]

    class Company(Model, collection="companies"):
        name: Field[str]
        ceo: Field[Person]

    doc = make_mock_document(
        "ACME",
        {
            "name": "Acme Corp",
            "ceo": {"name": "Jane", "address": {"street": "123 Main"}},
        },
    )
    mock_firestore_client.collection.return_value.document.return_value.get.return_value = doc

    ctx = Cendry(client=mock_firestore_client)
    company = ctx.get(Company, "ACME")

    assert company.ceo.name == "Jane"
    assert company.ceo.address.street == "123 Main"


# --- Ordering ---


def test_select_with_order_by(mock_firestore_client: MagicMock):
    docs = [make_mock_document("SF", SF_DATA)]
    order_mock = MagicMock()
    order_mock.stream.return_value = iter(docs)
    mock_firestore_client.collection.return_value.order_by.return_value = order_mock

    ctx = Cendry(client=mock_firestore_client)
    assert len(list(ctx.select(City, order_by=[Asc("population")]))) == 1
    mock_firestore_client.collection.return_value.order_by.assert_called_once_with(
        "population",
        direction="ASCENDING",
    )


# --- Cursors ---


def test_select_with_cursor_dict(mock_firestore_client: MagicMock):
    docs = [make_mock_document("SF", SF_DATA)]
    cursor_mock = MagicMock()
    cursor_mock.stream.return_value = iter(docs)
    mock_firestore_client.collection.return_value.start_after.return_value = cursor_mock

    ctx = Cendry(client=mock_firestore_client)
    assert len(list(ctx.select(City, start_after={"population": 500_000}))) == 1
    mock_firestore_client.collection.return_value.start_after.assert_called_once_with(
        {"population": 500_000},
    )


def test_select_with_cursor_model(mock_firestore_client: MagicMock):
    city_cursor = City(**{**SF_DATA, "name": "LA", "population": 3_900_000}, id="LA")
    docs = [make_mock_document("SF", SF_DATA)]
    cursor_mock = MagicMock()
    cursor_mock.stream.return_value = iter(docs)
    mock_firestore_client.collection.return_value.start_at.return_value = cursor_mock

    ctx = Cendry(client=mock_firestore_client)
    assert len(list(ctx.select(City, start_at=city_cursor))) == 1

    cursor_dict = mock_firestore_client.collection.return_value.start_at.call_args[0][0]
    assert "id" not in cursor_dict
    assert cursor_dict["name"] == "LA"


def test_select_with_end_cursors(mock_firestore_client: MagicMock):
    end_mock = MagicMock()
    end_mock2 = MagicMock()
    end_mock2.stream.return_value = iter([])
    end_mock.end_before.return_value = end_mock2
    mock_firestore_client.collection.return_value.end_at.return_value = end_mock

    ctx = Cendry(client=mock_firestore_client)
    result = list(
        ctx.select(
            City,
            end_at={"population": 1_000_000},
            end_before={"population": 2_000_000},
        )
    )
    assert len(result) == 0


# --- Composite filters ---


def test_select_with_and_filter(mock_firestore_client: MagicMock):
    docs = [make_mock_document("SF", SF_DATA)]
    query_mock = MagicMock()
    query_mock.stream.return_value = iter(docs)
    mock_firestore_client.collection.return_value.where.return_value = query_mock

    ctx = Cendry(client=mock_firestore_client)
    cities = list(ctx.select(City, And(City.state.eq("CA"), City.population.gt(500_000))))
    assert len(cities) == 1


def test_select_with_or_filter(mock_firestore_client: MagicMock):
    docs = [make_mock_document("SF", SF_DATA)]
    query_mock = MagicMock()
    query_mock.stream.return_value = iter(docs)
    mock_firestore_client.collection.return_value.where.return_value = query_mock

    ctx = Cendry(client=mock_firestore_client)
    cities = list(ctx.select(City, Or(City.state.eq("CA"), City.state.eq("NY"))))
    assert len(cities) == 1


def test_select_with_nested_composite(mock_firestore_client: MagicMock):
    query_mock = MagicMock()
    query_mock.stream.return_value = iter([])
    mock_firestore_client.collection.return_value.where.return_value = query_mock

    ctx = Cendry(client=mock_firestore_client)
    cities = list(
        ctx.select(
            City,
            Or(City.state.eq("CA"), And(City.country.eq("Japan"), City.population.gt(1_000_000))),
        )
    )
    assert len(cities) == 0


def test_select_with_raw_fieldfilter_in_or(mock_firestore_client: MagicMock):
    query_mock = MagicMock()
    query_mock.stream.return_value = iter([])
    mock_firestore_client.collection.return_value.where.return_value = query_mock

    ctx = Cendry(client=mock_firestore_client)
    list(
        ctx.select(
            City,
            Or(FieldFilter("state", "==", "CA"), FieldFilter("state", "==", "NY")),
        )
    )


def test_to_firestore_filter_or_branch(mock_firestore_client: MagicMock):
    query_mock = MagicMock()
    query_mock.stream.return_value = iter([])
    mock_firestore_client.collection.return_value.where.return_value = query_mock

    ctx = Cendry(client=mock_firestore_client)
    list(
        ctx.select(
            City,
            And(City.state.eq("CA"), Or(City.country.eq("USA"), City.country.eq("Japan"))),
        )
    )


# --- Error cases ---


def test_select_unknown_filter_raises(mock_firestore_client: MagicMock):
    ctx = Cendry(client=mock_firestore_client)
    with pytest.raises(CendryError, match="Unknown filter type"):
        list(ctx.select(City, "not_a_filter"))


# --- field() default_factory ---


def test_field_with_default_factory():
    class Item(Model, collection="items"):
        name: Field[str]
        tags: Field[list[str]] = cendry.field(default_factory=list)

    item = Item(name="test")
    assert item.tags == []


# --- resolve_map_type edge cases ---


def test_resolve_map_type_non_map():
    from cendry.serialize import resolve_map_type

    assert resolve_map_type(str) is None
    assert resolve_map_type("some_string") is None
    assert resolve_map_type(None) is None


# --- type_registry ---


def test_cendry_accepts_type_registry(mock_firestore_client: MagicMock):
    from cendry.types import TypeRegistry

    registry = TypeRegistry()
    ctx = Cendry(client=mock_firestore_client, type_registry=registry)
    assert ctx.type_registry is registry


def test_cendry_default_registry(mock_firestore_client: MagicMock):
    from cendry.types import default_registry

    ctx = Cendry(client=mock_firestore_client)
    assert ctx.type_registry is default_registry


@pytest.mark.anyio
async def test_async_cendry_accepts_type_registry(mock_firestore_client: MagicMock):
    from cendry.types import TypeRegistry

    registry = TypeRegistry()
    ctx = AsyncCendry(client=mock_firestore_client, type_registry=registry)
    assert ctx.type_registry is registry


# --- Context manager ---


def test_cendry_context_manager(mock_firestore_client: MagicMock):
    with Cendry(client=mock_firestore_client) as ctx:
        assert isinstance(ctx, Cendry)
    mock_firestore_client.close.assert_called_once()


@pytest.mark.anyio
async def test_async_cendry_context_manager(mock_firestore_client: MagicMock):
    mock_firestore_client.close = AsyncMock()
    async with AsyncCendry(client=mock_firestore_client) as ctx:
        assert isinstance(ctx, AsyncCendry)
    mock_firestore_client.close.assert_called_once()


# --- _validate_required_fields ---


def test_validate_required_fields_raises_on_none(mock_firestore_client: MagicMock):
    city = City(
        name=None,
        state="CA",
        country="USA",
        capital=False,
        population=870_000,
        regions=[],
    )
    ctx = Cendry(client=mock_firestore_client)
    with pytest.raises(CendryError, match="Required fields are None: name"):
        ctx._validate_required_fields(city)


def test_validate_required_fields_passes_with_defaults(mock_firestore_client: MagicMock):
    city = City(
        name="SF",
        state="CA",
        country="USA",
        capital=False,
        population=870_000,
        regions=[],
    )
    ctx = Cendry(client=mock_firestore_client)
    ctx._validate_required_fields(city)  # should not raise


def test_validate_required_fields_ignores_optional(mock_firestore_client: MagicMock):
    city = City(
        name="SF",
        state="CA",
        country="USA",
        capital=False,
        population=870_000,
        regions=[],
        nickname=None,
    )
    ctx = Cendry(client=mock_firestore_client)
    ctx._validate_required_fields(city)  # should not raise


# --- save ---


def test_save_with_explicit_id(mock_firestore_client: MagicMock):
    city = City(**SF_DATA, id="SF")
    ctx = Cendry(client=mock_firestore_client)

    result = ctx.save(city)

    doc_ref = mock_firestore_client.collection.return_value.document
    doc_ref.assert_called_with("SF")
    doc_ref.return_value.set.assert_called_once_with(to_dict(city, by_alias=True))
    assert result == doc_ref.return_value.id


def test_save_with_auto_id(mock_firestore_client: MagicMock):
    city = City(**SF_DATA)  # id=None
    doc_ref_mock = MagicMock()
    doc_ref_mock.id = "auto-123"
    mock_firestore_client.collection.return_value.document.return_value = doc_ref_mock

    ctx = Cendry(client=mock_firestore_client)
    result = ctx.save(city)

    mock_firestore_client.collection.return_value.document.assert_called_with()
    doc_ref_mock.set.assert_called_once()
    assert city.id == "auto-123"
    assert result == "auto-123"


def test_save_with_parent(mock_firestore_client: MagicMock):
    parent = City(**SF_DATA, id="SF")
    neighborhood = Neighborhood(name="Mission", population=60_000)
    doc_ref_mock = MagicMock()
    doc_ref_mock.id = "nb-123"
    parent_doc = mock_firestore_client.collection.return_value.document.return_value
    parent_doc.collection.return_value.document.return_value = doc_ref_mock

    ctx = Cendry(client=mock_firestore_client)
    result = ctx.save(neighborhood, parent=parent)

    parent_doc.collection.assert_called_with("neighborhoods")
    assert neighborhood.id == "nb-123"
    assert result == "nb-123"


def test_save_validates_required_fields(mock_firestore_client: MagicMock):
    city = City(
        name=None,
        state="CA",
        country="USA",
        capital=False,
        population=870_000,
        regions=[],
    )
    ctx = Cendry(client=mock_firestore_client)
    with pytest.raises(CendryError, match="Required fields are None"):
        ctx.save(city)


# --- create ---


def test_create_with_explicit_id(mock_firestore_client: MagicMock):
    city = City(**SF_DATA, id="SF")
    ctx = Cendry(client=mock_firestore_client)

    result = ctx.create(city)

    doc_ref = mock_firestore_client.collection.return_value.document
    doc_ref.assert_called_with("SF")
    doc_ref.return_value.create.assert_called_once_with(to_dict(city, by_alias=True))
    assert result == doc_ref.return_value.id


def test_create_with_auto_id(mock_firestore_client: MagicMock):
    city = City(**SF_DATA)  # id=None
    doc_ref_mock = MagicMock()
    doc_ref_mock.id = "auto-456"
    mock_firestore_client.collection.return_value.document.return_value = doc_ref_mock

    ctx = Cendry(client=mock_firestore_client)
    result = ctx.create(city)

    mock_firestore_client.collection.return_value.document.assert_called_with()
    doc_ref_mock.create.assert_called_once()
    assert city.id == "auto-456"
    assert result == "auto-456"


def test_create_raises_on_conflict(mock_firestore_client: MagicMock):
    from google.cloud.exceptions import Conflict

    city = City(**SF_DATA, id="SF")
    doc_ref = mock_firestore_client.collection.return_value.document.return_value
    doc_ref.id = "SF"
    doc_ref.create.side_effect = Conflict("already exists")

    ctx = Cendry(client=mock_firestore_client)
    with pytest.raises(DocumentAlreadyExistsError) as exc_info:
        ctx.create(city)

    assert exc_info.value.collection == "cities"
    assert exc_info.value.document_id == "SF"
    assert isinstance(exc_info.value.__cause__, Conflict)


def test_create_with_parent(mock_firestore_client: MagicMock):
    parent = City(**SF_DATA, id="SF")
    neighborhood = Neighborhood(name="Mission", population=60_000, id="MISSION")
    parent_doc = mock_firestore_client.collection.return_value.document.return_value
    sub_doc_ref = parent_doc.collection.return_value.document.return_value

    ctx = Cendry(client=mock_firestore_client)
    result = ctx.create(neighborhood, parent=parent)

    sub_doc_ref.create.assert_called_once()
    assert result == sub_doc_ref.id


def test_create_validates_required_fields(mock_firestore_client: MagicMock):
    city = City(
        name=None,
        state="CA",
        country="USA",
        capital=False,
        population=870_000,
        regions=[],
    )
    ctx = Cendry(client=mock_firestore_client)
    with pytest.raises(CendryError, match="Required fields are None"):
        ctx.create(city)


# --- delete ---


def test_delete_by_instance(mock_firestore_client: MagicMock):
    city = City(**SF_DATA, id="SF")
    ctx = Cendry(client=mock_firestore_client)

    ctx.delete(city)

    doc_ref = mock_firestore_client.collection.return_value.document
    doc_ref.assert_called_with("SF")
    doc_ref.return_value.delete.assert_called_once()


def test_delete_by_instance_no_id_raises(mock_firestore_client: MagicMock):
    city = City(**SF_DATA)  # id=None
    ctx = Cendry(client=mock_firestore_client)

    with pytest.raises(CendryError, match="Cannot delete a model instance with id=None"):
        ctx.delete(city)


def test_delete_by_class_and_id(mock_firestore_client: MagicMock):
    ctx = Cendry(client=mock_firestore_client)
    ctx.delete(City, "SF")

    doc_ref = mock_firestore_client.collection.return_value.document
    doc_ref.assert_called_with("SF")
    doc_ref.return_value.delete.assert_called_once()


def test_delete_by_class_silent_when_missing(mock_firestore_client: MagicMock):
    ctx = Cendry(client=mock_firestore_client)
    ctx.delete(City, "NOPE")  # should not raise


def test_delete_by_class_must_exist_raises(mock_firestore_client: MagicMock):
    doc = make_mock_document("NOPE", {}, exists=False)
    mock_firestore_client.collection.return_value.document.return_value.get.return_value = doc

    ctx = Cendry(client=mock_firestore_client)
    with pytest.raises(DocumentNotFoundError):
        ctx.delete(City, "NOPE", must_exist=True)


def test_delete_by_class_must_exist_passes(mock_firestore_client: MagicMock):
    doc = make_mock_document("SF", SF_DATA)
    mock_firestore_client.collection.return_value.document.return_value.get.return_value = doc

    ctx = Cendry(client=mock_firestore_client)
    ctx.delete(City, "SF", must_exist=True)

    mock_firestore_client.collection.return_value.document.return_value.delete.assert_called_once()


def test_delete_with_parent(mock_firestore_client: MagicMock):
    parent = City(**SF_DATA, id="SF")
    parent_doc = mock_firestore_client.collection.return_value.document.return_value
    sub_doc_ref = parent_doc.collection.return_value.document.return_value

    ctx = Cendry(client=mock_firestore_client)
    ctx.delete(Neighborhood, "MISSION", parent=parent)

    sub_doc_ref.delete.assert_called_once()


# --- async save ---


@pytest.mark.anyio
async def test_async_save_with_explicit_id(mock_firestore_client: MagicMock):
    city = City(**SF_DATA, id="SF")
    mock_firestore_client.collection.return_value.document.return_value.set = AsyncMock()

    ctx = AsyncCendry(client=mock_firestore_client)
    result = await ctx.save(city)

    mock_firestore_client.collection.return_value.document.assert_called_with("SF")
    assert result == mock_firestore_client.collection.return_value.document.return_value.id


@pytest.mark.anyio
async def test_async_save_with_auto_id(mock_firestore_client: MagicMock):
    city = City(**SF_DATA)  # id=None
    doc_ref_mock = MagicMock()
    doc_ref_mock.id = "auto-async-123"
    doc_ref_mock.set = AsyncMock()
    mock_firestore_client.collection.return_value.document.return_value = doc_ref_mock

    ctx = AsyncCendry(client=mock_firestore_client)
    result = await ctx.save(city)

    assert city.id == "auto-async-123"
    assert result == "auto-async-123"


@pytest.mark.anyio
async def test_async_save_with_parent(mock_firestore_client: MagicMock):
    parent = City(**SF_DATA, id="SF")
    neighborhood = Neighborhood(name="Mission", population=60_000)
    doc_ref_mock = MagicMock()
    doc_ref_mock.id = "nb-async-123"
    doc_ref_mock.set = AsyncMock()
    parent_doc = mock_firestore_client.collection.return_value.document.return_value
    parent_doc.collection.return_value.document.return_value = doc_ref_mock

    ctx = AsyncCendry(client=mock_firestore_client)
    result = await ctx.save(neighborhood, parent=parent)

    parent_doc.collection.assert_called_with("neighborhoods")
    assert neighborhood.id == "nb-async-123"
    assert result == "nb-async-123"


@pytest.mark.anyio
async def test_async_save_validates_required_fields(mock_firestore_client: MagicMock):
    city = City(
        name=None,
        state="CA",
        country="USA",
        capital=False,
        population=870_000,
        regions=[],
    )
    ctx = AsyncCendry(client=mock_firestore_client)
    with pytest.raises(CendryError, match="Required fields are None"):
        await ctx.save(city)


# --- async create ---


@pytest.mark.anyio
async def test_async_create_with_explicit_id(mock_firestore_client: MagicMock):
    city = City(**SF_DATA, id="SF")
    mock_firestore_client.collection.return_value.document.return_value.create = AsyncMock()

    ctx = AsyncCendry(client=mock_firestore_client)
    result = await ctx.create(city)

    mock_firestore_client.collection.return_value.document.return_value.create.assert_called_once()
    assert result == mock_firestore_client.collection.return_value.document.return_value.id


@pytest.mark.anyio
async def test_async_create_with_auto_id(mock_firestore_client: MagicMock):
    city = City(**SF_DATA)  # id=None
    doc_ref_mock = MagicMock()
    doc_ref_mock.id = "auto-async-456"
    doc_ref_mock.create = AsyncMock()
    mock_firestore_client.collection.return_value.document.return_value = doc_ref_mock

    ctx = AsyncCendry(client=mock_firestore_client)
    result = await ctx.create(city)

    mock_firestore_client.collection.return_value.document.assert_called_with()
    assert city.id == "auto-async-456"
    assert result == "auto-async-456"


@pytest.mark.anyio
async def test_async_create_with_parent(mock_firestore_client: MagicMock):
    parent = City(**SF_DATA, id="SF")
    neighborhood = Neighborhood(name="Mission", population=60_000, id="MISSION")
    parent_doc = mock_firestore_client.collection.return_value.document.return_value
    sub_doc_ref = parent_doc.collection.return_value.document.return_value
    sub_doc_ref.create = AsyncMock()

    ctx = AsyncCendry(client=mock_firestore_client)
    result = await ctx.create(neighborhood, parent=parent)

    sub_doc_ref.create.assert_called_once()
    assert result == sub_doc_ref.id


@pytest.mark.anyio
async def test_async_create_raises_on_conflict(mock_firestore_client: MagicMock):
    from google.cloud.exceptions import Conflict

    city = City(**SF_DATA, id="SF")
    doc_ref = mock_firestore_client.collection.return_value.document.return_value
    doc_ref.id = "SF"
    doc_ref.create = AsyncMock(side_effect=Conflict("already exists"))

    ctx = AsyncCendry(client=mock_firestore_client)
    with pytest.raises(DocumentAlreadyExistsError) as exc_info:
        await ctx.create(city)

    assert isinstance(exc_info.value.__cause__, Conflict)


@pytest.mark.anyio
async def test_async_create_validates_required_fields(mock_firestore_client: MagicMock):
    city = City(
        name=None,
        state="CA",
        country="USA",
        capital=False,
        population=870_000,
        regions=[],
    )
    ctx = AsyncCendry(client=mock_firestore_client)
    with pytest.raises(CendryError, match="Required fields are None"):
        await ctx.create(city)


# --- async delete ---


@pytest.mark.anyio
async def test_async_delete_by_instance(mock_firestore_client: MagicMock):
    city = City(**SF_DATA, id="SF")
    mock_firestore_client.collection.return_value.document.return_value.delete = AsyncMock()

    ctx = AsyncCendry(client=mock_firestore_client)
    await ctx.delete(city)

    mock_firestore_client.collection.return_value.document.return_value.delete.assert_called_once()


@pytest.mark.anyio
async def test_async_delete_by_instance_no_id_raises(mock_firestore_client: MagicMock):
    city = City(**SF_DATA)  # id=None
    ctx = AsyncCendry(client=mock_firestore_client)

    with pytest.raises(CendryError, match="Cannot delete a model instance with id=None"):
        await ctx.delete(city)


@pytest.mark.anyio
async def test_async_delete_by_class_and_id(mock_firestore_client: MagicMock):
    mock_firestore_client.collection.return_value.document.return_value.delete = AsyncMock()

    ctx = AsyncCendry(client=mock_firestore_client)
    await ctx.delete(City, "SF")

    mock_firestore_client.collection.return_value.document.assert_called_with("SF")
    mock_firestore_client.collection.return_value.document.return_value.delete.assert_called_once()


@pytest.mark.anyio
async def test_async_delete_by_class_must_exist_raises(mock_firestore_client: MagicMock):
    doc = make_mock_document("NOPE", {}, exists=False)
    mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
        return_value=doc,
    )
    mock_firestore_client.collection.return_value.document.return_value.delete = AsyncMock()

    ctx = AsyncCendry(client=mock_firestore_client)
    with pytest.raises(DocumentNotFoundError):
        await ctx.delete(City, "NOPE", must_exist=True)


@pytest.mark.anyio
async def test_async_delete_by_class_must_exist_passes(mock_firestore_client: MagicMock):
    doc = make_mock_document("SF", SF_DATA)
    mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
        return_value=doc,
    )
    mock_firestore_client.collection.return_value.document.return_value.delete = AsyncMock()

    ctx = AsyncCendry(client=mock_firestore_client)
    await ctx.delete(City, "SF", must_exist=True)

    mock_firestore_client.collection.return_value.document.return_value.delete.assert_called_once()


@pytest.mark.anyio
async def test_async_delete_with_parent(mock_firestore_client: MagicMock):
    parent = City(**SF_DATA, id="SF")
    parent_doc = mock_firestore_client.collection.return_value.document.return_value
    sub_doc_ref = parent_doc.collection.return_value.document.return_value
    sub_doc_ref.delete = AsyncMock()

    ctx = AsyncCendry(client=mock_firestore_client)
    await ctx.delete(Neighborhood, "MISSION", parent=parent)

    sub_doc_ref.delete.assert_called_once()


# --- Registry threading ---


class Celsius:
    def __init__(self, value: float) -> None:
        self.value = value


class CelsiusHandler(BaseTypeHandler):
    def serialize(self, value: Celsius) -> float:
        return value.value

    def deserialize(self, value: float) -> Celsius:
        return Celsius(value)


default_registry.register(Celsius, handler=CelsiusHandler())


class Weather(Model, collection="weather_ctx"):
    city: Field[str]
    temp: Field[Celsius]


def test_get_uses_context_registry(mock_firestore_client: MagicMock):
    custom = TypeRegistry()
    custom.register(Celsius, handler=CelsiusHandler())
    doc = make_mock_document("w1", {"city": "SF", "temp": 20.5})
    mock_firestore_client.collection.return_value.document.return_value.get.return_value = doc

    ctx = Cendry(client=mock_firestore_client, type_registry=custom)
    weather = ctx.get(Weather, "w1")

    assert isinstance(weather.temp, Celsius)
    assert weather.temp.value == 20.5


def test_save_uses_context_registry(mock_firestore_client: MagicMock):
    custom = TypeRegistry()
    custom.register(Celsius, handler=CelsiusHandler())
    weather = Weather(city="SF", temp=Celsius(20.5), id="w1")

    ctx = Cendry(client=mock_firestore_client, type_registry=custom)
    ctx.save(weather)

    call_args = mock_firestore_client.collection.return_value.document.return_value.set.call_args
    data = call_args[0][0]
    assert data["temp"] == 20.5


def test_select_iteration_uses_context_registry(mock_firestore_client: MagicMock):
    custom = TypeRegistry()
    custom.register(Celsius, handler=CelsiusHandler())
    docs = [make_mock_document("w1", {"city": "SF", "temp": 20.5})]
    mock_firestore_client.collection.return_value.stream.return_value = iter(docs)

    ctx = Cendry(client=mock_firestore_client, type_registry=custom)
    results = list(ctx.select(Weather))

    assert len(results) == 1
    assert isinstance(results[0].temp, Celsius)


@pytest.mark.anyio
async def test_async_get_uses_context_registry(mock_firestore_client: MagicMock):
    custom = TypeRegistry()
    custom.register(Celsius, handler=CelsiusHandler())
    doc = make_mock_document("w1", {"city": "SF", "temp": 20.5})
    mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
        return_value=doc,
    )

    ctx = AsyncCendry(client=mock_firestore_client, type_registry=custom)
    weather = await ctx.get(Weather, "w1")

    assert isinstance(weather.temp, Celsius)
    assert weather.temp.value == 20.5


@pytest.mark.anyio
async def test_async_save_uses_context_registry(mock_firestore_client: MagicMock):
    custom = TypeRegistry()
    custom.register(Celsius, handler=CelsiusHandler())
    weather = Weather(city="SF", temp=Celsius(20.5), id="w1")
    mock_firestore_client.collection.return_value.document.return_value.set = AsyncMock()

    ctx = AsyncCendry(client=mock_firestore_client, type_registry=custom)
    await ctx.save(weather)

    call_args = mock_firestore_client.collection.return_value.document.return_value.set.call_args
    data = call_args[0][0]
    assert data["temp"] == 20.5


@pytest.mark.anyio
async def test_async_select_iteration_uses_context_registry(mock_firestore_client: MagicMock):
    custom = TypeRegistry()
    custom.register(Celsius, handler=CelsiusHandler())
    docs = [make_mock_document("w1", {"city": "SF", "temp": 20.5})]

    async def mock_stream():
        for d in docs:
            yield d

    mock_firestore_client.collection.return_value.stream = mock_stream

    ctx = AsyncCendry(client=mock_firestore_client, type_registry=custom)
    results = [item async for item in ctx.select(Weather)]

    assert len(results) == 1
    assert isinstance(results[0].temp, Celsius)


# --- update ---


def test_update_by_instance(mock_firestore_client: MagicMock):
    city = City(**SF_DATA, id="SF")
    ctx = Cendry(client=mock_firestore_client)

    ctx.update(city, {"name": "New Name", "population": 1_000_000})

    doc_ref = mock_firestore_client.collection.return_value.document
    doc_ref.assert_called_with("SF")
    doc_ref.return_value.update.assert_called_once()
    call_data = doc_ref.return_value.update.call_args[0][0]
    assert call_data["name"] == "New Name"
    assert call_data["population"] == 1_000_000


def test_update_by_class_and_id(mock_firestore_client: MagicMock):
    ctx = Cendry(client=mock_firestore_client)

    ctx.update(City, "SF", {"name": "New Name"})

    doc_ref = mock_firestore_client.collection.return_value.document
    doc_ref.assert_called_with("SF")
    doc_ref.return_value.update.assert_called_once()


def test_update_dot_notation(mock_firestore_client: MagicMock):
    city = City(**SF_DATA, id="SF")
    ctx = Cendry(client=mock_firestore_client)

    ctx.update(city, {"mayor.name": "Jane"})

    call_data = (
        mock_firestore_client.collection.return_value.document.return_value.update.call_args[0][0]
    )
    assert "mayor.name" in call_data


def test_update_alias_resolution(mock_firestore_client: MagicMock):
    from cendry import field as cendry_field

    class AliasCity(Model, collection="alias_cities"):
        display_name: Field[str] = cendry_field(alias="displayName")

    city = AliasCity(display_name="SF", id="SF")
    ctx = Cendry(client=mock_firestore_client)

    ctx.update(city, {"display_name": "San Francisco"})

    call_data = (
        mock_firestore_client.collection.return_value.document.return_value.update.call_args[0][0]
    )
    assert "displayName" in call_data
    assert "display_name" not in call_data


def test_update_with_sentinel(mock_firestore_client: MagicMock):
    from google.cloud.firestore import DELETE_FIELD, SERVER_TIMESTAMP

    city = City(**SF_DATA, id="SF")
    ctx = Cendry(client=mock_firestore_client)

    ctx.update(city, {"nickname": DELETE_FIELD, "name": SERVER_TIMESTAMP})

    call_data = (
        mock_firestore_client.collection.return_value.document.return_value.update.call_args[0][0]
    )
    assert call_data["nickname"] is DELETE_FIELD
    assert call_data["name"] is SERVER_TIMESTAMP


def test_update_with_transform(mock_firestore_client: MagicMock):
    from google.cloud.firestore import Increment

    city = City(**SF_DATA, id="SF")
    ctx = Cendry(client=mock_firestore_client)
    inc = Increment(1)

    ctx.update(city, {"population": inc})

    call_data = (
        mock_firestore_client.collection.return_value.document.return_value.update.call_args[0][0]
    )
    assert call_data["population"] is inc


def test_update_instance_no_id_raises(mock_firestore_client: MagicMock):
    city = City(**SF_DATA)  # id=None
    ctx = Cendry(client=mock_firestore_client)

    with pytest.raises(CendryError, match="Cannot update a model instance with id=None"):
        ctx.update(city, {"name": "New"})


def test_update_missing_doc_raises(mock_firestore_client: MagicMock):
    city = City(**SF_DATA, id="SF")
    mock_firestore_client.collection.return_value.document.return_value.update.side_effect = (
        NotFound("not found")
    )

    ctx = Cendry(client=mock_firestore_client)
    with pytest.raises(DocumentNotFoundError) as exc_info:
        ctx.update(city, {"name": "New"})

    assert isinstance(exc_info.value.__cause__, NotFound)


def test_update_with_parent(mock_firestore_client: MagicMock):
    parent = City(**SF_DATA, id="SF")
    parent_doc = mock_firestore_client.collection.return_value.document.return_value
    sub_doc_ref = parent_doc.collection.return_value.document.return_value

    ctx = Cendry(client=mock_firestore_client)
    ctx.update(Neighborhood, "MISSION", {"population": 65_000}, parent=parent)

    sub_doc_ref.update.assert_called_once()


def test_update_with_custom_type_handler(mock_firestore_client: MagicMock):
    custom = TypeRegistry()
    custom.register(Celsius, handler=CelsiusHandler())
    weather = Weather(city="SF", temp=Celsius(20.5), id="w1")

    ctx = Cendry(client=mock_firestore_client, type_registry=custom)
    ctx.update(weather, {"temp": Celsius(25.0)})

    call_data = (
        mock_firestore_client.collection.return_value.document.return_value.update.call_args[0][0]
    )
    assert call_data["temp"] == 25.0


# --- refresh ---


def test_refresh_mutates_instance(mock_firestore_client: MagicMock):
    city = City(**SF_DATA, id="SF")
    updated_data = {**SF_DATA, "name": "San Fran", "population": 900_000}
    doc = make_mock_document("SF", updated_data)
    mock_firestore_client.collection.return_value.document.return_value.get.return_value = doc

    ctx = Cendry(client=mock_firestore_client)
    ctx.refresh(city)

    assert city.name == "San Fran"
    assert city.population == 900_000
    assert city.id == "SF"


def test_refresh_no_id_raises(mock_firestore_client: MagicMock):
    city = City(**SF_DATA)  # id=None
    ctx = Cendry(client=mock_firestore_client)

    with pytest.raises(CendryError, match="Cannot refresh a model instance with id=None"):
        ctx.refresh(city)


def test_refresh_missing_doc_raises(mock_firestore_client: MagicMock):
    city = City(**SF_DATA, id="SF")
    doc = make_mock_document("SF", {}, exists=False)
    mock_firestore_client.collection.return_value.document.return_value.get.return_value = doc

    ctx = Cendry(client=mock_firestore_client)
    with pytest.raises(DocumentNotFoundError):
        ctx.refresh(city)


def test_refresh_with_parent(mock_firestore_client: MagicMock):
    parent = City(**SF_DATA, id="SF")
    neighborhood = Neighborhood(name="Mission", population=60_000, id="MISSION")
    updated_data = {"name": "Mission District", "population": 65_000}
    doc = make_mock_document("MISSION", updated_data)
    parent_doc = mock_firestore_client.collection.return_value.document.return_value
    parent_doc.collection.return_value.document.return_value.get.return_value = doc

    ctx = Cendry(client=mock_firestore_client)
    ctx.refresh(neighborhood, parent=parent)

    assert neighborhood.name == "Mission District"
    assert neighborhood.population == 65_000


# --- async update ---


@pytest.mark.anyio
async def test_async_update_by_instance(mock_firestore_client: MagicMock):
    city = City(**SF_DATA, id="SF")
    mock_firestore_client.collection.return_value.document.return_value.update = AsyncMock()

    ctx = AsyncCendry(client=mock_firestore_client)
    await ctx.update(city, {"name": "New Name"})

    mock_firestore_client.collection.return_value.document.return_value.update.assert_called_once()


@pytest.mark.anyio
async def test_async_update_by_class_and_id(mock_firestore_client: MagicMock):
    mock_firestore_client.collection.return_value.document.return_value.update = AsyncMock()

    ctx = AsyncCendry(client=mock_firestore_client)
    await ctx.update(City, "SF", {"name": "New Name"})

    mock_firestore_client.collection.return_value.document.return_value.update.assert_called_once()


@pytest.mark.anyio
async def test_async_update_instance_no_id_raises(mock_firestore_client: MagicMock):
    city = City(**SF_DATA)  # id=None
    ctx = AsyncCendry(client=mock_firestore_client)

    with pytest.raises(CendryError, match="Cannot update a model instance with id=None"):
        await ctx.update(city, {"name": "New"})


@pytest.mark.anyio
async def test_async_update_missing_doc_raises(mock_firestore_client: MagicMock):
    city = City(**SF_DATA, id="SF")
    mock_firestore_client.collection.return_value.document.return_value.update = AsyncMock(
        side_effect=NotFound("not found")
    )

    ctx = AsyncCendry(client=mock_firestore_client)
    with pytest.raises(DocumentNotFoundError) as exc_info:
        await ctx.update(city, {"name": "New"})

    assert isinstance(exc_info.value.__cause__, NotFound)


@pytest.mark.anyio
async def test_async_update_with_parent(mock_firestore_client: MagicMock):
    parent = City(**SF_DATA, id="SF")
    parent_doc = mock_firestore_client.collection.return_value.document.return_value
    sub_doc_ref = parent_doc.collection.return_value.document.return_value
    sub_doc_ref.update = AsyncMock()

    ctx = AsyncCendry(client=mock_firestore_client)
    await ctx.update(Neighborhood, "MISSION", {"population": 65_000}, parent=parent)

    sub_doc_ref.update.assert_called_once()


# --- async refresh ---


@pytest.mark.anyio
async def test_async_refresh_mutates_instance(mock_firestore_client: MagicMock):
    city = City(**SF_DATA, id="SF")
    updated_data = {**SF_DATA, "name": "San Fran", "population": 900_000}
    doc = make_mock_document("SF", updated_data)
    mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
        return_value=doc,
    )

    ctx = AsyncCendry(client=mock_firestore_client)
    await ctx.refresh(city)

    assert city.name == "San Fran"
    assert city.population == 900_000


@pytest.mark.anyio
async def test_async_refresh_no_id_raises(mock_firestore_client: MagicMock):
    city = City(**SF_DATA)
    ctx = AsyncCendry(client=mock_firestore_client)

    with pytest.raises(CendryError, match="Cannot refresh a model instance with id=None"):
        await ctx.refresh(city)


@pytest.mark.anyio
async def test_async_refresh_missing_doc_raises(mock_firestore_client: MagicMock):
    city = City(**SF_DATA, id="SF")
    doc = make_mock_document("SF", {}, exists=False)
    mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
        return_value=doc,
    )

    ctx = AsyncCendry(client=mock_firestore_client)
    with pytest.raises(DocumentNotFoundError):
        await ctx.refresh(city)
