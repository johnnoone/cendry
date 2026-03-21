import pytest

import cendry
from cendry import Field, Map, Model
from cendry import field as cendry_field
from cendry.serialize import deserialize, from_dict, to_dict
from cendry.types import BaseTypeHandler, TypeRegistry, default_registry


class Mayor(Map):
    name: Field[str]
    since: Field[int]


class City(Model, collection="cities_ser"):
    name: Field[str]
    state: Field[str]
    country: Field[str]
    capital: Field[bool]
    population: Field[int]
    regions: Field[list[str]]
    nickname: Field[str | None] = cendry_field(default=None)
    mayor: Field[Mayor | None] = cendry_field(default=None)


CITY_DATA = {
    "name": "SF",
    "state": "CA",
    "country": "USA",
    "capital": False,
    "population": 870_000,
    "regions": ["west"],
}


def test_from_dict_simple():
    city = from_dict(City, CITY_DATA)
    assert city.name == "SF"
    assert city.id is None


def test_from_dict_with_id():
    city = from_dict(City, CITY_DATA, doc_id="123")
    assert city.id == "123"


def test_from_dict_nested_map():
    city = from_dict(
        City,
        {
            **CITY_DATA,
            "mayor": {"name": "London Breed", "since": 2018},
        },
    )
    assert isinstance(city.mayor, Mayor)
    assert city.mayor.name == "London Breed"


def test_from_dict_missing_fields():
    with pytest.raises(TypeError, match="missing required fields"):
        from_dict(City, {"name": "SF"})


def test_from_dict_missing_fields_message():
    with pytest.raises(TypeError, match="state, country, capital, population, regions"):
        from_dict(City, {"name": "SF"})


def test_from_dict_exported():
    assert hasattr(cendry, "from_dict")


# --- Custom registry tests ---


class Celsius:
    def __init__(self, value: float) -> None:
        self.value = value


class CelsiusHandler(BaseTypeHandler):
    def serialize(self, value: Celsius) -> float:
        return value.value

    def deserialize(self, value: float) -> Celsius:
        return Celsius(value)


default_registry.register(Celsius, handler=CelsiusHandler())


class Weather(Model, collection="weather"):
    city: Field[str]
    temp: Field[Celsius]


def test_to_dict_with_custom_registry():
    custom = TypeRegistry()
    custom.register(Celsius, handler=CelsiusHandler())
    weather = Weather(city="SF", temp=Celsius(20.5))

    result = to_dict(weather, registry=custom)
    assert result["temp"] == 20.5


def test_from_dict_with_custom_registry():
    custom = TypeRegistry()
    custom.register(Celsius, handler=CelsiusHandler())

    weather = from_dict(Weather, {"city": "SF", "temp": 20.5}, registry=custom)
    assert isinstance(weather.temp, Celsius)
    assert weather.temp.value == 20.5


def test_deserialize_with_custom_registry():
    custom = TypeRegistry()
    custom.register(Celsius, handler=CelsiusHandler())

    weather = deserialize(Weather, "w1", {"city": "SF", "temp": 20.5}, registry=custom)
    assert isinstance(weather.temp, Celsius)
    assert weather.temp.value == 20.5


def test_to_dict_default_registry_unchanged():
    """Existing behavior: no registry param uses default_registry."""
    city = from_dict(City, CITY_DATA)
    result = to_dict(city)
    assert result["name"] == "SF"
