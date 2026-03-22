"""Integration tests for query operations against the Firestore emulator."""

import pytest

from cendry import Cendry, Field, Model


class City(Model, collection="test_query_cities"):
    name: Field[str]
    state: Field[str]
    population: Field[int]


@pytest.fixture
def seeded_ctx(firestore_client, clean_collection):
    """Seed test data and return a Cendry context."""
    clean_collection("test_query_cities")
    ctx = Cendry(client=firestore_client)
    ctx.save_many(
        [
            City(name="San Francisco", state="CA", population=870_000, id="SF"),
            City(name="Los Angeles", state="CA", population=3_900_000, id="LA"),
            City(name="New York", state="NY", population=8_300_000, id="NYC"),
            City(name="Chicago", state="IL", population=2_700_000, id="CHI"),
        ]
    )
    return ctx


def test_select_all(seeded_ctx):
    cities = seeded_ctx.select(City).to_list()
    assert len(cities) == 4


def test_select_with_filter(seeded_ctx):
    ca_cities = seeded_ctx.select(City, City.state == "CA").to_list()
    assert len(ca_cities) == 2
    assert all(c.state == "CA" for c in ca_cities)


def test_select_with_limit(seeded_ctx):
    cities = seeded_ctx.select(City).limit(2).to_list()
    assert len(cities) == 2


def test_query_first(seeded_ctx):
    city = seeded_ctx.select(City, City.state == "NY").first()
    assert city is not None
    assert city.name == "New York"


def test_query_first_none(seeded_ctx):
    city = seeded_ctx.select(City, City.state == "TX").first()
    assert city is None


def test_query_count(seeded_ctx):
    n = seeded_ctx.select(City, City.state == "CA").count()
    assert n == 2


def test_query_exists(seeded_ctx):
    assert seeded_ctx.select(City, City.state == "CA").exists()
    assert not seeded_ctx.select(City, City.state == "TX").exists()


def test_get_many(seeded_ctx):
    cities = seeded_ctx.get_many(City, ["SF", "NYC"])
    assert len(cities) == 2
    names = {c.name for c in cities}
    assert "San Francisco" in names
    assert "New York" in names
