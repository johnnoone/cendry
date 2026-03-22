"""Integration tests for advanced query features against the Firestore emulator."""

import pytest

from cendry import Asc, Cendry, Desc, Field, Model
from cendry.metadata import get_metadata


class City(Model, collection="test_adv_query_cities"):
    name: Field[str]
    state: Field[str]
    population: Field[int]


@pytest.fixture
def seeded_ctx(firestore_client, clean_collection):
    clean_collection("test_adv_query_cities")
    ctx = Cendry(client=firestore_client)
    ctx.save_many(
        [
            City(name="San Francisco", state="CA", population=870_000, id="SF"),
            City(name="Los Angeles", state="CA", population=3_900_000, id="LA"),
            City(name="New York", state="NY", population=8_300_000, id="NYC"),
            City(name="Chicago", state="IL", population=2_700_000, id="CHI"),
            City(name="Houston", state="TX", population=2_300_000, id="HOU"),
        ]
    )
    return ctx


def test_query_chaining(seeded_ctx):
    cities = (
        seeded_ctx.select(City)
        .filter(City.state == "CA")
        .order_by(City.population.desc())
        .limit(10)
        .to_list()
    )
    assert len(cities) == 2
    assert cities[0].name == "Los Angeles"
    assert cities[1].name == "San Francisco"


def test_query_order_by_asc(seeded_ctx):
    cities = seeded_ctx.select(City).order_by(Asc("population")).limit(2).to_list()
    assert len(cities) == 2
    assert cities[0].population <= cities[1].population


def test_query_order_by_desc(seeded_ctx):
    cities = seeded_ctx.select(City).order_by(Desc("population")).limit(2).to_list()
    assert len(cities) == 2
    assert cities[0].population >= cities[1].population


def test_query_one(seeded_ctx):
    city = seeded_ctx.select(City, City.state == "NY").one()
    assert city.name == "New York"


def test_query_exists_true(seeded_ctx):
    assert seeded_ctx.select(City, City.state == "TX").exists()


def test_query_exists_false(seeded_ctx):
    assert not seeded_ctx.select(City, City.state == "ZZ").exists()


def test_query_count(seeded_ctx):
    assert seeded_ctx.select(City).count() == 5
    assert seeded_ctx.select(City, City.state == "CA").count() == 2


def test_query_paginate(seeded_ctx):
    pages = list(seeded_ctx.select(City).order_by(Asc("name")).paginate(page_size=2))
    assert len(pages) == 3  # 5 items / 2 per page = 3 pages
    total = sum(len(p) for p in pages)
    assert total == 5


def test_query_first_returns_model(seeded_ctx):
    city = seeded_ctx.select(City, City.state == "IL").first()
    assert city is not None
    assert city.name == "Chicago"


def test_query_first_none(seeded_ctx):
    assert seeded_ctx.select(City, City.state == "ZZ").first() is None


def test_query_metadata_on_iteration(seeded_ctx):
    cities = seeded_ctx.select(City).limit(1).to_list()
    assert len(cities) == 1
    meta = get_metadata(cities[0])
    assert meta.update_time is not None


def test_project_returns_dicts(seeded_ctx):
    results = seeded_ctx.select(City, City.state == "CA").project("name").to_list()
    assert len(results) == 2
    assert all(isinstance(r, dict) for r in results)
    assert all("name" in r for r in results)
    assert all("id" in r for r in results)


def test_project_first(seeded_ctx):
    result = seeded_ctx.select(City, City.state == "NY").project("name").first()
    assert result is not None
    assert result["name"] == "New York"


def test_find_returns_none_for_missing(seeded_ctx):
    assert seeded_ctx.find(City, "NONEXISTENT") is None
