import dataclasses
import datetime

import pytest

from cendry import Field, Map, Model, field
from cendry.filters import Filter

# --- Map ---


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


# --- Model ---


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

    assert City(name="SF").id is None


def test_model_id_can_be_set():
    class City(Model, collection="cities"):
        name: Field[str]

    assert City(id="123", name="SF").id == "123"


def test_model_collection_stored():
    class City(Model, collection="cities"):
        name: Field[str]

    assert City.__collection__ == "cities"


def test_model_with_default():
    class City(Model, collection="cities"):
        name: Field[str]
        nickname: Field[str | None] = field(default=None)

    assert City(name="SF").nickname is None


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


# --- Type validation at definition ---


def test_model_rejects_invalid_field_type():
    with pytest.raises(TypeError, match="complex"):

        class Bad(Model, collection="bad"):
            val: Field[complex]


def test_map_rejects_invalid_field_type():
    with pytest.raises(TypeError, match="complex"):

        class Bad(Map):
            val: Field[complex]


def test_model_accepts_list_str():
    class Good(Model, collection="good_list"):
        tags: Field[list[str]]

    assert Good.__collection__ == "good_list"


def test_model_accepts_dict_str_int():
    class Good(Model, collection="good_dict"):
        data: Field[dict[str, int]]

    assert Good.__collection__ == "good_dict"


# --- Field descriptor filters ---


def test_field_descriptor_eq():
    class City(Model, collection="cities"):
        state: Field[str]

    assert isinstance(City.state.eq("CA"), Filter)


def test_field_descriptor_ne():
    class City(Model, collection="cities"):
        state: Field[str]

    assert isinstance(City.state.ne("CA"), Filter)


def test_field_descriptor_gt():
    class City(Model, collection="cities"):
        population: Field[int]

    assert isinstance(City.population.gt(1_000_000), Filter)


def test_field_descriptor_gte():
    class City(Model, collection="cities"):
        population: Field[int]

    assert isinstance(City.population.gte(1_000_000), Filter)


def test_field_descriptor_lt():
    class City(Model, collection="cities"):
        population: Field[int]

    assert isinstance(City.population.lt(500), Filter)


def test_field_descriptor_lte():
    class City(Model, collection="cities"):
        population: Field[int]

    assert isinstance(City.population.lte(500), Filter)


def test_field_descriptor_array_contains():
    class City(Model, collection="cities"):
        regions: Field[list[str]]

    assert isinstance(City.regions.array_contains("west_coast"), Filter)


def test_field_descriptor_array_contains_any():
    class City(Model, collection="cities"):
        regions: Field[list[str]]

    assert isinstance(City.regions.array_contains_any(["west_coast", "east_coast"]), Filter)


def test_field_descriptor_is_in():
    class City(Model, collection="cities"):
        country: Field[str]

    assert isinstance(City.country.is_in(["USA", "Japan"]), Filter)


def test_field_descriptor_not_in():
    class City(Model, collection="cities"):
        country: Field[str]

    assert isinstance(City.country.not_in(["China"]), Filter)


def test_field_descriptor_composition_and():
    class City(Model, collection="cities"):
        state: Field[str]
        population: Field[int]

    assert isinstance(City.state.ne("CA") & City.population.gt(1_000_000), Filter)


def test_field_descriptor_composition_or():
    class City(Model, collection="cities"):
        state: Field[str]
        country: Field[str]

    assert isinstance(City.state.eq("CA") | City.country.eq("Japan"), Filter)


# --- Dunder filter shortcuts ---


def test_field_descriptor_dunder_eq():
    class City(Model, collection="cities"):
        state: Field[str]

    result = City.state == "CA"
    assert isinstance(result, Filter)
    assert result.op == "=="


def test_field_descriptor_dunder_ne():
    class City(Model, collection="cities"):
        state: Field[str]

    result = City.state != "CA"
    assert isinstance(result, Filter)
    assert result.op == "!="


def test_field_descriptor_dunder_gt():
    class City(Model, collection="cities"):
        population: Field[int]

    result = City.population > 100
    assert isinstance(result, Filter)
    assert result.op == ">"


def test_field_descriptor_dunder_ge():
    class City(Model, collection="cities"):
        population: Field[int]

    result = City.population >= 100
    assert isinstance(result, Filter)
    assert result.op == ">="


def test_field_descriptor_dunder_lt():
    class City(Model, collection="cities"):
        population: Field[int]

    result = City.population < 100
    assert isinstance(result, Filter)
    assert result.op == "<"


def test_field_descriptor_dunder_le():
    class City(Model, collection="cities"):
        population: Field[int]

    result = City.population <= 100
    assert isinstance(result, Filter)
    assert result.op == "<="


def test_field_descriptor_not_hashable():
    class City(Model, collection="cities"):
        state: Field[str]

    with pytest.raises(TypeError):
        hash(City.state)


# --- auto_now / auto_now_add ---


def test_field_auto_now_and_auto_now_add_mutually_exclusive():
    with pytest.raises(ValueError, match="Cannot combine auto_now and auto_now_add"):
        field(auto_now=True, auto_now_add=True)


def test_field_auto_now_with_explicit_default_raises():
    with pytest.raises(ValueError, match="Cannot combine auto_now/auto_now_add with explicit"):
        field(auto_now=True, default=None)


def test_field_auto_now_add_with_explicit_default_factory_raises():
    with pytest.raises(ValueError, match="Cannot combine auto_now/auto_now_add with explicit"):
        field(auto_now_add=True, default_factory=datetime.datetime.now)


def test_field_auto_now_sets_implicit_default_none():
    class Event(Model, collection="events"):
        ts: Field[datetime.datetime | None] = field(auto_now=True)

    e = Event()
    assert e.ts is None


def test_field_auto_now_add_sets_implicit_default_none():
    class Event(Model, collection="events"):
        ts: Field[datetime.datetime | None] = field(auto_now_add=True)

    e = Event()
    assert e.ts is None
