"""Tests for DX improvements v2: owner, alias, .asc()/.desc(), to_dict,
get_many, enum, repr, order_by/limit on Query, pagination."""

import enum
from unittest.mock import MagicMock

import pytest

import cendry
from cendry import (
    AsyncCendry,
    Cendry,
    DocumentNotFoundError,
    Field,
    Map,
    Model,
)
from cendry import field as cendry_field
from cendry.query import Asc, Desc
from cendry.serialize import from_dict, to_dict
from cendry.types import TypeRegistry
from tests.conftest import City, make_mock_document

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


# --- Owner tracking ---


def test_field_descriptor_has_owner():
    class C(Model, collection="test_owner"):
        state: Field[str]

    assert C.state.owner is C


def test_field_descriptor_owner_with_inheritance():
    class Base(Map):
        name: Field[str]

    class C(Base, Model, collection="test_inherit"):
        state: Field[str]

    assert C.name.owner is C
    assert C.state.owner is C


def test_field_descriptor_repr():
    class C(Model, collection="test_repr_fd"):
        state: Field[str]

    assert repr(C.state) == "C.state"


# --- Alias ---


def test_field_descriptor_alias_default():
    class C(Model, collection="test_alias_default"):
        state: Field[str]

    assert C.state.alias == "state"


def test_field_descriptor_alias_custom():
    class C(Model, collection="test_alias_custom"):
        name: Field[str] = cendry_field(alias="displayName")

    assert C.name.alias == "displayName"
    assert C.name.field_name == "name"


def test_field_descriptor_filter_uses_alias():
    class C(Model, collection="test_alias_filter"):
        name: Field[str] = cendry_field(alias="displayName")

    result = C.name == "SF"
    assert result.field_name == "displayName"


# --- .asc() / .desc() ---


def test_field_descriptor_asc():
    class C(Model, collection="test_asc"):
        population: Field[int]

    result = C.population.asc()
    assert isinstance(result, Asc)
    assert result.field == "population"


def test_field_descriptor_desc():
    class C(Model, collection="test_desc"):
        population: Field[int]

    result = C.population.desc()
    assert isinstance(result, Desc)
    assert result.field == "population"


def test_asc_uses_alias():
    class C(Model, collection="test_asc_alias"):
        name: Field[str] = cendry_field(alias="displayName")

    result = C.name.asc()
    assert result.field == "displayName"


def test_asc_repr():
    class C(Model, collection="test_asc_repr"):
        population: Field[int]

    assert repr(C.population.asc()) == "C.population.asc()"


def test_desc_repr():
    class C(Model, collection="test_desc_repr"):
        population: Field[int]

    assert repr(C.population.desc()) == "C.population.desc()"


def test_asc_repr_string():
    assert repr(Asc("population")) == 'Asc("population")'


def test_desc_repr_string():
    assert repr(Desc("population")) == 'Desc("population")'


# --- Enum support ---


def test_enum_is_valid():
    class Status(enum.Enum):
        ACTIVE = "active"

    registry = TypeRegistry()
    registry.validate("status", Status, "TestModel")


def test_int_enum_is_valid():
    class Priority(enum.IntEnum):
        HIGH = 1

    registry = TypeRegistry()
    registry.validate("priority", Priority, "TestModel")


def test_str_enum_is_valid():
    class Color(enum.StrEnum):
        RED = "red"

    registry = TypeRegistry()
    registry.validate("color", Color, "TestModel")


def test_enum_field_on_model():
    class Status(enum.Enum):
        ACTIVE = "active"

    class User(Model, collection="test_enum_model"):
        name: Field[str]
        status: Field[Status]

    assert User.__collection__ == "test_enum_model"


# --- field() enum_by ---


def test_field_enum_by():
    class Role(enum.Enum):
        ADMIN = "admin"

    class User(Model, collection="test_enum_by"):
        role: Field[Role] = cendry_field(enum_by="name")

    # Metadata stored for future conversion
    import dataclasses

    for f in dataclasses.fields(User):
        if f.name == "role":
            assert f.metadata.get("cendry_enum_by") == "name"


# --- to_dict ---


def test_to_dict_simple():
    city = from_dict(City, SF_DATA)
    result = to_dict(city)
    assert result["name"] == "San Francisco"
    assert "id" not in result


def test_to_dict_include_id():
    city = from_dict(City, SF_DATA, doc_id="123")
    result = to_dict(city, include_id=True)
    assert result["id"] == "123"


def test_to_dict_nested_map():
    city = from_dict(City, {**SF_DATA, "mayor": {"name": "Jane", "since": 2020}})
    result = to_dict(city)
    assert isinstance(result["mayor"], dict)
    assert result["mayor"]["name"] == "Jane"


def test_to_dict_by_alias():
    class AliasedModel(Model, collection="test_to_dict_alias"):
        name: Field[str] = cendry_field(alias="displayName")

    obj = AliasedModel(name="test")
    assert to_dict(obj)["name"] == "test"
    assert to_dict(obj, by_alias=True)["displayName"] == "test"


def test_to_dict_exported():
    assert hasattr(cendry, "to_dict")


# --- from_dict with alias ---


def test_from_dict_by_alias():
    class AliasedModel(Model, collection="test_from_dict_alias"):
        name: Field[str] = cendry_field(alias="displayName")

    obj = from_dict(AliasedModel, {"displayName": "test"}, by_alias=True)
    assert obj.name == "test"


def test_from_dict_python_names():
    class AliasedModel(Model, collection="test_from_dict_python"):
        name: Field[str] = cendry_field(alias="displayName")

    obj = from_dict(AliasedModel, {"name": "test"})
    assert obj.name == "test"


# --- Deserialization uses alias ---


def test_deserialize_uses_alias(mock_firestore_client: MagicMock):
    class AliasedCity(Model, collection="test_deser_alias"):
        name: Field[str] = cendry_field(alias="displayName")

    doc = make_mock_document("SF", {"displayName": "San Francisco"})
    mock_firestore_client.collection.return_value.document.return_value.get.return_value = doc

    ctx = Cendry(client=mock_firestore_client)
    city = ctx.get(AliasedCity, "SF")
    assert city.name == "San Francisco"


# --- get_many ---


def test_get_many(mock_firestore_client: MagicMock):
    docs = [
        make_mock_document("SF", SF_DATA, exists=True),
        make_mock_document("LA", {**SF_DATA, "name": "Los Angeles"}, exists=True),
    ]
    mock_firestore_client.get_all.return_value = docs

    ctx = Cendry(client=mock_firestore_client)
    cities = ctx.get_many(City, ["SF", "LA"])
    assert len(cities) == 2
    assert cities[0].name == "San Francisco"


def test_get_many_missing_raises(mock_firestore_client: MagicMock):
    doc_found = make_mock_document("SF", SF_DATA, exists=True)
    doc_missing = make_mock_document("NOPE", {}, exists=False)
    mock_firestore_client.get_all.return_value = [doc_found, doc_missing]

    ctx = Cendry(client=mock_firestore_client)
    with pytest.raises(DocumentNotFoundError):
        ctx.get_many(City, ["SF", "NOPE"])


@pytest.mark.anyio
async def test_async_get_many(mock_firestore_client: MagicMock):
    docs = [make_mock_document("SF", SF_DATA, exists=True)]

    async def mock_get_all(refs, **kwargs):
        for d in docs:
            yield d

    mock_firestore_client.get_all = mock_get_all

    ctx = AsyncCendry(client=mock_firestore_client)
    cities = await ctx.get_many(City, ["SF"])
    assert len(cities) == 1


# --- Chainable order_by / limit ---


def test_query_order_by(mock_firestore_client: MagicMock):
    order_mock = _mock_stream([make_mock_document("SF", SF_DATA)])
    mock_firestore_client.collection.return_value.order_by.return_value = order_mock
    ctx = Cendry(client=mock_firestore_client)
    cities = ctx.select(City).order_by(City.population).to_list()
    assert len(cities) == 1


def test_query_order_by_desc(mock_firestore_client: MagicMock):
    order_mock = _mock_stream([make_mock_document("SF", SF_DATA)])
    mock_firestore_client.collection.return_value.order_by.return_value = order_mock
    ctx = Cendry(client=mock_firestore_client)
    ctx.select(City).order_by(City.population.desc()).to_list()
    mock_firestore_client.collection.return_value.order_by.assert_called_once_with(
        "population",
        direction="DESCENDING",
    )


def test_query_chainable_limit(mock_firestore_client: MagicMock):
    limit_mock = _mock_stream([make_mock_document("SF", SF_DATA)])
    mock_firestore_client.collection.return_value.limit.return_value = limit_mock
    ctx = Cendry(client=mock_firestore_client)
    cities = ctx.select(City).limit(5).to_list()
    assert len(cities) == 1


def test_query_order_by_immutable(mock_firestore_client: MagicMock):
    mock_firestore_client.collection.return_value.stream.return_value = iter([])
    order_mock = MagicMock()
    order_mock.stream.return_value = iter([])
    mock_firestore_client.collection.return_value.order_by.return_value = order_mock
    ctx = Cendry(client=mock_firestore_client)
    q1 = ctx.select(City)
    q2 = q1.order_by(City.population)
    assert q1 is not q2


# --- Query repr ---


def test_query_repr_empty(mock_firestore_client: MagicMock):
    ctx = Cendry(client=mock_firestore_client)
    assert repr(ctx.select(City)) == "Query(City)"


def test_query_repr_with_filter(mock_firestore_client: MagicMock):
    where_mock = MagicMock()
    mock_firestore_client.collection.return_value.where.return_value = where_mock
    ctx = Cendry(client=mock_firestore_client)
    q = ctx.select(City).filter(City.state == "CA")
    assert "City.state == 'CA'" in repr(q)


def test_query_repr_with_order_and_limit(mock_firestore_client: MagicMock):
    order_mock = MagicMock()
    limit_mock = MagicMock()
    order_mock.limit.return_value = limit_mock
    mock_firestore_client.collection.return_value.order_by.return_value = order_mock
    ctx = Cendry(client=mock_firestore_client)
    q = ctx.select(City).order_by(City.population).limit(10)
    r = repr(q)
    assert "order_by=[City.population.asc()]" in r
    assert "limit=10" in r


def test_async_query_repr(mock_firestore_client: MagicMock):
    ctx = AsyncCendry(client=mock_firestore_client)
    assert repr(ctx.select(City)) == "AsyncQuery(City)"


def test_async_query_repr_with_order_and_limit(mock_firestore_client: MagicMock):
    order_mock = MagicMock()
    limit_mock = MagicMock()
    order_mock.limit.return_value = limit_mock
    mock_firestore_client.collection.return_value.order_by.return_value = order_mock
    ctx = AsyncCendry(client=mock_firestore_client)
    q = ctx.select(City).order_by(City.population).limit(10)
    r = repr(q)
    assert "AsyncQuery(" in r
    assert "order_by=[City.population.asc()]" in r
    assert "limit=10" in r


# --- Pagination ---


def test_query_paginate(mock_firestore_client: MagicMock):
    page1_docs = [make_mock_document("1", SF_DATA), make_mock_document("2", SF_DATA)]
    page2_docs = [make_mock_document("3", SF_DATA)]

    call_count = 0

    def make_limit_mock(n):
        nonlocal call_count
        call_count += 1
        mock = MagicMock()
        if call_count == 1:
            mock.stream.return_value = iter(page1_docs)
        else:
            mock.stream.return_value = iter(page2_docs)
        mock.start_after.return_value = mock
        mock.limit.return_value = mock
        return mock

    mock_firestore_client.collection.return_value.limit.side_effect = make_limit_mock
    mock_firestore_client.collection.return_value.start_after.return_value = (
        mock_firestore_client.collection.return_value
    )

    ctx = Cendry(client=mock_firestore_client)
    pages = list(ctx.select(City).paginate(page_size=2))
    assert len(pages) == 2
    assert len(pages[0]) == 2
    assert len(pages[1]) == 1


def test_field_descriptor_repr_no_owner():
    from cendry.model import FieldDescriptor

    fd = FieldDescriptor("test")
    assert repr(fd) == "?.test"


def test_from_dict_remap_alias():
    """from_dict with by_alias=False remaps Python names to aliases."""

    class AliasedModel(Model, collection="test_remap"):
        name: Field[str] = cendry_field(alias="displayName")

    obj = from_dict(AliasedModel, {"name": "hello"}, by_alias=False)
    assert obj.name == "hello"


@pytest.mark.anyio
async def test_async_query_order_by(mock_firestore_client: MagicMock):
    async def mock_stream():
        for d in [make_mock_document("SF", SF_DATA)]:
            yield d

    order_mock = MagicMock()
    order_mock.stream = mock_stream
    mock_firestore_client.collection.return_value.order_by.return_value = order_mock
    ctx = AsyncCendry(client=mock_firestore_client)
    cities = await ctx.select(City).order_by(City.population).to_list()
    assert len(cities) == 1


@pytest.mark.anyio
async def test_async_query_limit(mock_firestore_client: MagicMock):
    async def mock_stream():
        for d in [make_mock_document("SF", SF_DATA)]:
            yield d

    limit_mock = MagicMock()
    limit_mock.stream = mock_stream
    mock_firestore_client.collection.return_value.limit.return_value = limit_mock
    ctx = AsyncCendry(client=mock_firestore_client)
    cities = await ctx.select(City).limit(5).to_list()
    assert len(cities) == 1


@pytest.mark.anyio
async def test_async_get_many_missing_raises(mock_firestore_client: MagicMock):
    async def mock_get_all(refs, **kwargs):
        yield make_mock_document("SF", SF_DATA, exists=True)
        yield make_mock_document("NOPE", {}, exists=False)

    mock_firestore_client.get_all = mock_get_all
    ctx = AsyncCendry(client=mock_firestore_client)
    with pytest.raises(DocumentNotFoundError):
        await ctx.get_many(City, ["SF", "NOPE"])


def test_query_paginate_empty(mock_firestore_client: MagicMock):
    empty_mock = MagicMock()
    empty_mock.stream.return_value = iter([])
    mock_firestore_client.collection.return_value.limit.return_value = empty_mock

    ctx = Cendry(client=mock_firestore_client)
    pages = list(ctx.select(City).paginate(page_size=10))
    assert len(pages) == 0


@pytest.mark.anyio
async def test_async_query_paginate(mock_firestore_client: MagicMock):
    page1_docs = [make_mock_document("1", SF_DATA)]

    async def mock_stream():
        for d in page1_docs:
            yield d

    limit_mock = MagicMock()
    limit_mock.stream = mock_stream
    limit_mock.limit.return_value = limit_mock
    mock_firestore_client.collection.return_value.limit.return_value = limit_mock

    ctx = AsyncCendry(client=mock_firestore_client)
    pages: list[list[City]] = []
    async for page in ctx.select(City).paginate(page_size=10):
        pages.append(page)  # noqa: PERF401
    # page has 1 item < page_size=10, so it's the last page
    assert len(pages) == 1
    assert len(pages[0]) == 1


@pytest.mark.anyio
async def test_async_query_paginate_empty(mock_firestore_client: MagicMock):
    async def mock_stream():
        return
        yield  # make it an async generator

    limit_mock = MagicMock()
    limit_mock.stream = mock_stream
    mock_firestore_client.collection.return_value.limit.return_value = limit_mock

    ctx = AsyncCendry(client=mock_firestore_client)
    pages: list[list[City]] = []
    async for page in ctx.select(City).paginate(page_size=10):
        pages.append(page)  # noqa: PERF401
    assert len(pages) == 0


@pytest.mark.anyio
async def test_async_query_paginate_multipage(mock_firestore_client: MagicMock):
    page1_docs = [make_mock_document("1", SF_DATA), make_mock_document("2", SF_DATA)]
    page2_docs = [make_mock_document("3", SF_DATA)]
    call_count = 0

    def make_limit_mock(n):
        nonlocal call_count
        call_count += 1

        async def stream():
            docs = page1_docs if call_count == 1 else page2_docs
            for d in docs:
                yield d

        mock = MagicMock()
        mock.stream = stream
        mock.start_after.return_value = mock
        mock.limit.side_effect = make_limit_mock
        return mock

    mock_firestore_client.collection.return_value.limit.side_effect = make_limit_mock
    mock_firestore_client.collection.return_value.start_after.return_value = (
        mock_firestore_client.collection.return_value
    )

    ctx = AsyncCendry(client=mock_firestore_client)
    pages: list[list[City]] = []
    async for page in ctx.select(City).paginate(page_size=2):
        pages.append(page)  # noqa: PERF401
    assert len(pages) == 2
