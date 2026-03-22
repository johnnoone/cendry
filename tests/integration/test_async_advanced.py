"""Integration tests for async queries, transactions, and projections."""

import os

import pytest
from google.cloud.firestore import AsyncClient

from cendry import Asc, AsyncCendry, Field, Model

from .conftest import PROJECT_ID


class City(Model, collection="test_async_adv"):
    name: Field[str]
    state: Field[str]
    population: Field[int]


@pytest.fixture
async def seeded_async_ctx(firestore_emulator, clean_collection):
    clean_collection("test_async_adv")
    os.environ["FIRESTORE_EMULATOR_HOST"] = firestore_emulator
    client = AsyncClient(project=PROJECT_ID)
    ctx = AsyncCendry(client=client)
    await ctx.save_many(
        [
            City(name="SF", state="CA", population=870_000, id="SF"),
            City(name="LA", state="CA", population=3_900_000, id="LA"),
            City(name="NYC", state="NY", population=8_300_000, id="NYC"),
            City(name="CHI", state="IL", population=2_700_000, id="CHI"),
        ]
    )
    yield ctx
    client.close()  # type: ignore[unused-awaitable]


@pytest.mark.anyio
async def test_async_query_filter_chain(seeded_async_ctx):
    cities = await (
        seeded_async_ctx.select(City)
        .filter(City.state == "CA")
        .order_by(City.population.desc())
        .limit(10)
        .to_list()
    )
    assert len(cities) == 2
    assert cities[0].name == "LA"


@pytest.mark.anyio
async def test_async_query_first(seeded_async_ctx):
    city = await seeded_async_ctx.select(City, City.state == "NY").first()
    assert city is not None
    assert city.name == "NYC"


@pytest.mark.anyio
async def test_async_query_first_none(seeded_async_ctx):
    assert await seeded_async_ctx.select(City, City.state == "ZZ").first() is None


@pytest.mark.anyio
async def test_async_query_count(seeded_async_ctx):
    n = await seeded_async_ctx.select(City, City.state == "CA").count()
    assert n == 2


@pytest.mark.anyio
async def test_async_query_exists(seeded_async_ctx):
    assert await seeded_async_ctx.select(City, City.state == "CA").exists()
    assert not await seeded_async_ctx.select(City, City.state == "ZZ").exists()


@pytest.mark.anyio
async def test_async_query_one(seeded_async_ctx):
    city = await seeded_async_ctx.select(City, City.state == "IL").one()
    assert city.name == "CHI"


@pytest.mark.anyio
async def test_async_project(seeded_async_ctx):
    results = await seeded_async_ctx.select(City, City.state == "CA").project("name").to_list()
    assert len(results) == 2
    assert all(isinstance(r, dict) for r in results)
    assert all("name" in r for r in results)


@pytest.mark.anyio
async def test_async_project_first(seeded_async_ctx):
    result = await seeded_async_ctx.select(City, City.state == "NY").project("name").first()
    assert result is not None
    assert result["name"] == "NYC"


@pytest.mark.anyio
async def test_async_transaction_context_manager(seeded_async_ctx):
    async with seeded_async_ctx.transaction() as txn:
        city = await txn.get(City, "SF")
        txn.update(city, {"population": 999_000})

    fetched = await seeded_async_ctx.get(City, "SF")
    assert fetched.population == 999_000


@pytest.mark.anyio
async def test_async_transaction_callback(seeded_async_ctx):
    async def transfer(txn):
        sf = await txn.get(City, "SF")
        la = await txn.get(City, "LA")
        txn.update(sf, {"population": sf.population - 100})
        txn.update(la, {"population": la.population + 100})

    await seeded_async_ctx.transaction(transfer)

    sf = await seeded_async_ctx.get(City, "SF")
    la = await seeded_async_ctx.get(City, "LA")
    assert sf.population == 869_900
    assert la.population == 3_900_100


@pytest.mark.anyio
async def test_async_get_many(seeded_async_ctx):
    cities = await seeded_async_ctx.get_many(City, ["SF", "NYC"])
    assert len(cities) == 2


@pytest.mark.anyio
async def test_async_query_paginate(seeded_async_ctx):
    pages = [
        page
        async for page in seeded_async_ctx.select(City).order_by(Asc("name")).paginate(page_size=2)
    ]
    assert len(pages) == 2  # 4 items / 2 per page
    total = sum(len(p) for p in pages)
    assert total == 4
