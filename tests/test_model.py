import dataclasses

import pytest

from cendry import Model, Map, Field, field
from cendry.filters import Filter


# --- Map tests ---


def test_map_is_dataclass():
    class Mayor(Map):
        name: Field[str]
        since: Field[int]

    assert dataclasses.is_dataclass(Mayor)


def test_map_instantiation():
    class Mayor(Map):
        name: Field[str]
        since: Field[int]

    m = Mayor(name="Jane", since=2020)
    assert m.name == "Jane"
    assert m.since == 2020


def test_map_has_no_id():
    class Mayor(Map):
        name: Field[str]

    assert "id" not in {f.name for f in dataclasses.fields(Mayor)}


def test_map_nested_in_map():
    class Address(Map):
        street: Field[str]

    class Person(Map):
        name: Field[str]
        address: Field[Address]

    p = Person(name="Jane", address=Address(street="123 Main"))
    assert p.address.street == "123 Main"


# --- Model tests ---


def test_model_requires_collection():
    with pytest.raises(TypeError):
        class Bad(Model):
            name: Field[str]


def test_model_is_dataclass():
    class City(Model, collection="cities"):
        name: Field[str]

    assert dataclasses.is_dataclass(City)


def test_model_has_id():
    class City(Model, collection="cities"):
        name: Field[str]

    c = City(name="SF")
    assert c.id is None


def test_model_id_can_be_set():
    class City(Model, collection="cities"):
        name: Field[str]

    c = City(id="123", name="SF")
    assert c.id == "123"


def test_model_collection_stored():
    class City(Model, collection="cities"):
        name: Field[str]

    assert City.__collection__ == "cities"


def test_model_with_default():
    class City(Model, collection="cities"):
        name: Field[str]
        nickname: Field[str | None] = field(default=None)

    c = City(name="SF")
    assert c.nickname is None


def test_model_cannot_nest_model():
    class City(Model, collection="cities"):
        name: Field[str]

    with pytest.raises(TypeError, match="cannot nest"):
        class Country(Model, collection="countries"):
            city: Field[City]


def test_map_cannot_nest_model():
    class City(Model, collection="cities"):
        name: Field[str]

    with pytest.raises(TypeError, match="cannot nest"):
        class Info(Map):
            city: Field[City]


# --- Field descriptor filter method tests ---


def test_field_descriptor_eq():
    class City(Model, collection="cities"):
        state: Field[str]

    result = City.state.eq("CA")
    assert isinstance(result, Filter)


def test_field_descriptor_ne():
    class City(Model, collection="cities"):
        state: Field[str]

    result = City.state.ne("CA")
    assert isinstance(result, Filter)


def test_field_descriptor_gt():
    class City(Model, collection="cities"):
        population: Field[int]

    result = City.population.gt(1000000)
    assert isinstance(result, Filter)


def test_field_descriptor_gte():
    class City(Model, collection="cities"):
        population: Field[int]

    result = City.population.gte(1000000)
    assert isinstance(result, Filter)


def test_field_descriptor_lt():
    class City(Model, collection="cities"):
        population: Field[int]

    result = City.population.lt(500)
    assert isinstance(result, Filter)


def test_field_descriptor_lte():
    class City(Model, collection="cities"):
        population: Field[int]

    result = City.population.lte(500)
    assert isinstance(result, Filter)


def test_field_descriptor_array_contains():
    class City(Model, collection="cities"):
        regions: Field[list[str]]

    result = City.regions.array_contains("west_coast")
    assert isinstance(result, Filter)


def test_field_descriptor_array_contains_any():
    class City(Model, collection="cities"):
        regions: Field[list[str]]

    result = City.regions.array_contains_any(["west_coast", "east_coast"])
    assert isinstance(result, Filter)


def test_field_descriptor_is_in():
    class City(Model, collection="cities"):
        country: Field[str]

    result = City.country.is_in(["USA", "Japan"])
    assert isinstance(result, Filter)


def test_field_descriptor_not_in():
    class City(Model, collection="cities"):
        country: Field[str]

    result = City.country.not_in(["China"])
    assert isinstance(result, Filter)


def test_field_descriptor_composition_and():
    class City(Model, collection="cities"):
        state: Field[str]
        population: Field[int]

    result = City.state.ne("CA") & City.population.gt(1000000)
    assert isinstance(result, Filter)


def test_field_descriptor_composition_or():
    class City(Model, collection="cities"):
        state: Field[str]
        country: Field[str]

    result = City.state.eq("CA") | City.country.eq("Japan")
    assert isinstance(result, Filter)
