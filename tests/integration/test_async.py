"""Integration tests for async operations against the Firestore emulator."""

import os

import pytest
from google.cloud.firestore import AsyncClient

from cendry import AsyncCendry, Field, Model
from cendry.metadata import get_metadata

from .conftest import PROJECT_ID


class City(Model, collection="test_async_cities"):
    name: Field[str]
    state: Field[str]
    population: Field[int]


@pytest.fixture
async def async_ctx(firestore_emulator, clean_collection):
    clean_collection("test_async_cities")
    os.environ["FIRESTORE_EMULATOR_HOST"] = firestore_emulator
    client = AsyncClient(project=PROJECT_ID)
    ctx = AsyncCendry(client=client)
    yield ctx
    client.close()  # type: ignore[unused-awaitable]


@pytest.mark.anyio
async def test_async_save_and_get(async_ctx):
    city = City(name="SF", state="CA", population=870_000)
    await async_ctx.save(city)
    assert city.id is not None

    fetched = await async_ctx.get(City, city.id)
    assert fetched.name == "SF"


@pytest.mark.anyio
async def test_async_find_returns_none(async_ctx):
    assert await async_ctx.find(City, "NONEXISTENT") is None


@pytest.mark.anyio
async def test_async_create_and_get(async_ctx):
    city = City(name="LA", state="CA", population=3_900_000, id="async-la")
    await async_ctx.create(city)

    fetched = await async_ctx.get(City, "async-la")
    assert fetched.name == "LA"


@pytest.mark.anyio
async def test_async_update(async_ctx):
    city = City(name="NYC", state="NY", population=8_300_000, id="async-nyc")
    await async_ctx.save(city)
    await async_ctx.update(city, {"population": 8_400_000})

    fetched = await async_ctx.get(City, "async-nyc")
    assert fetched.population == 8_400_000


@pytest.mark.anyio
async def test_async_delete(async_ctx):
    city = City(name="Del", state="XX", population=0, id="async-del")
    await async_ctx.save(city)
    await async_ctx.delete(city)

    assert await async_ctx.find(City, "async-del") is None


@pytest.mark.anyio
async def test_async_refresh(async_ctx, firestore_emulator):
    city = City(name="Refresh", state="XX", population=100, id="async-refresh")
    await async_ctx.save(city)

    # Update directly via sync client to simulate external change
    from google.cloud.firestore import Client

    sync_client = Client(project=PROJECT_ID)
    sync_client.collection("test_async_cities").document("async-refresh").update(
        {"population": 999}
    )
    sync_client.close()

    await async_ctx.refresh(city)
    assert city.population == 999


@pytest.mark.anyio
async def test_async_select(async_ctx):
    await async_ctx.save_many(
        [
            City(name="A", state="CA", population=1, id="a"),
            City(name="B", state="CA", population=2, id="b"),
            City(name="C", state="NY", population=3, id="c"),
        ]
    )

    cities = [city async for city in async_ctx.select(City, City.state == "CA")]
    assert len(cities) == 2


@pytest.mark.anyio
async def test_async_select_to_list(async_ctx):
    await async_ctx.save_many(
        [
            City(name="X", state="TX", population=1, id="x"),
            City(name="Y", state="TX", population=2, id="y"),
        ]
    )
    cities = await async_ctx.select(City, City.state == "TX").to_list()
    assert len(cities) == 2


@pytest.mark.anyio
async def test_async_save_many_and_delete_many(async_ctx):
    cities = [City(name=f"c{i}", state="XX", population=i, id=f"batch-{i}") for i in range(3)]
    await async_ctx.save_many(cities)

    fetched = await async_ctx.select(City, City.state == "XX").to_list()
    assert len(fetched) == 3

    await async_ctx.delete_many(cities)
    fetched = await async_ctx.select(City, City.state == "XX").to_list()
    assert len(fetched) == 0


@pytest.mark.anyio
async def test_async_batch(async_ctx):
    await async_ctx.save(City(name="Keep", state="ZZ", population=1, id="keep"))

    async with async_ctx.batch() as batch:
        batch.save(City(name="New", state="ZZ", population=2, id="new"))
        batch.delete(City, "keep")

    assert await async_ctx.find(City, "new") is not None
    assert await async_ctx.find(City, "keep") is None


@pytest.mark.anyio
async def test_async_metadata(async_ctx):
    city = City(name="Meta", state="XX", population=1, id="async-meta")
    await async_ctx.save(city)

    meta = get_metadata(city)
    assert meta.update_time is not None

    fetched = await async_ctx.get(City, "async-meta")
    meta2 = get_metadata(fetched)
    assert meta2.update_time is not None
    assert meta2.create_time is not None
