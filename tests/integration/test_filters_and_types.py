"""Integration tests for filters, composition, and type validation."""

import pytest

from cendry import And, Cendry, Field, FieldFilter, Model, Or


class City(Model, collection="test_filter_cities"):
    name: Field[str]
    state: Field[str]
    population: Field[int]
    tags: Field[list[str]]


@pytest.fixture
def seeded_ctx(firestore_client, clean_collection):
    clean_collection("test_filter_cities")
    ctx = Cendry(client=firestore_client)
    ctx.save_many(
        [
            City(name="SF", state="CA", population=870_000, tags=["west"], id="SF"),
            City(name="LA", state="CA", population=3_900_000, tags=["west", "large"], id="LA"),
            City(name="NYC", state="NY", population=8_300_000, tags=["east", "large"], id="NYC"),
            City(name="CHI", state="IL", population=2_700_000, tags=["central"], id="CHI"),
        ]
    )
    return ctx


def test_field_filter_raw(seeded_ctx):
    cities = seeded_ctx.select(City, FieldFilter("state", "==", "CA")).to_list()
    assert len(cities) == 2


def test_field_descriptor_filter(seeded_ctx):
    cities = seeded_ctx.select(City, City.state == "CA").to_list()
    assert len(cities) == 2


def test_field_descriptor_gt(seeded_ctx):
    cities = seeded_ctx.select(City, City.population > 2_000_000).to_list()
    assert len(cities) == 3


def test_and_filter(seeded_ctx):
    cities = seeded_ctx.select(
        City, And(City.state == "CA", City.population > 1_000_000)
    ).to_list()
    assert len(cities) == 1
    assert cities[0].name == "LA"


def test_or_filter(seeded_ctx):
    cities = seeded_ctx.select(City, Or(City.state == "CA", City.state == "NY")).to_list()
    assert len(cities) == 3


def test_multiple_varargs_filters(seeded_ctx):
    cities = seeded_ctx.select(City, City.state == "CA", City.population > 1_000_000).to_list()
    assert len(cities) == 1


def test_query_filter_chaining(seeded_ctx):
    cities = (
        seeded_ctx.select(City)
        .filter(City.state == "CA")
        .filter(City.population > 1_000_000)
        .to_list()
    )
    assert len(cities) == 1
