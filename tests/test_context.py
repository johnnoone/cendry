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
from cendry.serialize import to_dict
from tests.conftest import City, Mayor, Neighborhood, make_mock_document

SF_DATA = {
    "name": "San Francisco",
    "state": "CA",
    "country": "USA",
    "capital": False,
    "population": 870000,
    "regions": ["west_coast"],
}


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
        name=None,  # type: ignore[arg-type]
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
        name=None,  # type: ignore[arg-type]
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
        name=None,  # type: ignore[arg-type]
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
