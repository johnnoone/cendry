import pytest

import cendry
from cendry import Field, Map, Model
from cendry import field as cendry_field
from cendry.serialize import (
    deserialize,
    from_dict,
    resolve_field_hint,
    resolve_field_path,
    serialize_update_value,
    to_dict,
    validate_required_fields,
)
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


# --- serialize_update_value / resolve_field_path ---


class AliasedCity(Model, collection="aliased_cities"):
    name: Field[str]
    city_name: Field[str] = cendry_field(alias="cityName")


def test_serialize_update_value_simple():
    """Simple values pass through unchanged."""
    custom = TypeRegistry()
    assert serialize_update_value("hello", registry=custom) == "hello"
    assert serialize_update_value(42, registry=custom) == 42
    assert serialize_update_value(True, registry=custom) is True


def test_serialize_update_value_with_handler():
    """Custom-typed values are serialized via handler."""
    custom = TypeRegistry()
    custom.register(Celsius, handler=CelsiusHandler())
    result = serialize_update_value(Celsius(20.5), registry=custom)
    assert result == 20.5


def test_serialize_update_value_sentinel():
    """Firestore sentinels pass through unchanged."""
    from google.cloud.firestore import DELETE_FIELD, SERVER_TIMESTAMP

    custom = TypeRegistry()
    assert serialize_update_value(DELETE_FIELD, registry=custom) is DELETE_FIELD
    assert serialize_update_value(SERVER_TIMESTAMP, registry=custom) is SERVER_TIMESTAMP


def test_serialize_update_value_transform():
    """Firestore transforms pass through unchanged."""
    from google.cloud.firestore import ArrayUnion, Increment

    custom = TypeRegistry()
    inc = Increment(1)
    assert serialize_update_value(inc, registry=custom) is inc
    au = ArrayUnion(["tag"])
    assert serialize_update_value(au, registry=custom) is au


def test_resolve_field_path_simple():
    """Simple field names pass through."""
    assert resolve_field_path(AliasedCity, "name") == "name"


def test_resolve_field_path_alias():
    """Python field names are converted to Firestore aliases."""
    assert resolve_field_path(AliasedCity, "city_name") == "cityName"


def test_resolve_field_path_dot_notation():
    """First segment of dot-notation path is alias-resolved."""
    assert resolve_field_path(AliasedCity, "city_name.sub") == "cityName.sub"


def test_resolve_field_path_unknown():
    """Unknown field names pass through unchanged."""
    assert resolve_field_path(AliasedCity, "unknown_field") == "unknown_field"


# --- validate_required_fields ---


def test_validate_required_fields_raises():
    city = City(
        name=None,
        state="CA",
        country="USA",
        capital=False,
        population=870_000,
        regions=[],
    )
    with pytest.raises(Exception, match="Required fields are None: name"):
        validate_required_fields(city)


def test_validate_required_fields_passes():
    city = City(**CITY_DATA)
    validate_required_fields(city)  # should not raise


# --- resolve_field_path with nested Map aliases ---


class AliasedMayor(Map):
    full_name: Field[str] = cendry_field(alias="fullName")
    since: Field[int]


class CityWithAliasedMayor(Model, collection="cities_nested"):
    name: Field[str]
    mayor: Field[AliasedMayor | None] = cendry_field(default=None)


def test_resolve_field_path_nested_map_alias():
    """Nested Map field aliases are resolved recursively."""
    assert resolve_field_path(CityWithAliasedMayor, "mayor.full_name") == "mayor.fullName"


def test_resolve_field_path_nested_map_no_alias():
    """Nested Map field without alias passes through."""
    assert resolve_field_path(CityWithAliasedMayor, "mayor.since") == "mayor.since"


def test_resolve_field_path_nested_non_map():
    """Dot-notation on a non-Map field passes through unchanged."""
    assert resolve_field_path(CityWithAliasedMayor, "name.sub") == "name.sub"


# --- resolve_field_hint ---


def test_resolve_field_hint_simple():
    hint = resolve_field_hint(City, "name")
    assert hint is str


def test_resolve_field_hint_nested_map():
    hint = resolve_field_hint(CityWithAliasedMayor, "mayor.full_name")
    assert hint is str


def test_resolve_field_hint_unknown():
    assert resolve_field_hint(City, "nonexistent") is None


def test_resolve_field_hint_nested_non_map():
    assert resolve_field_hint(City, "name.sub") is None


# --- serialize_update_value with hint ---


def test_serialize_update_value_with_hint_list():
    """Container types serialize elements when hint is provided."""
    custom = TypeRegistry()
    custom.register(Celsius, handler=CelsiusHandler())
    result = serialize_update_value(
        [Celsius(20.5), Celsius(30.0)], hint=list[Celsius], registry=custom
    )
    assert result == [20.5, 30.0]


def test_serialize_update_value_without_hint_list():
    """Without hint, list elements are not serialized through handlers."""
    custom = TypeRegistry()
    custom.register(Celsius, handler=CelsiusHandler())
    result = serialize_update_value([Celsius(20.5)], registry=custom)
    # Without hint, type(value) is list, no generic info — elements pass through
    assert len(result) == 1
    assert isinstance(result[0], Celsius)
