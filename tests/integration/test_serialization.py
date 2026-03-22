"""Integration tests for serialization, type handlers, and aliases against the emulator."""

import enum

from cendry import Cendry, Field, Map, Model
from cendry import field as cendry_field
from cendry.serialize import from_dict, to_dict
from cendry.types import BaseTypeHandler, TypeRegistry


class Mayor(Map):
    name: Field[str]
    since: Field[int]


class Status(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class AliasedCity(Model, collection="test_ser_cities"):
    display_name: Field[str] = cendry_field(alias="displayName")
    state: Field[str]
    population: Field[int]
    mayor: Field[Mayor | None] = cendry_field(default=None)
    status: Field[Status | None] = cendry_field(default=None)


def test_save_and_get_with_alias(firestore_client, clean_collection):
    clean_collection("test_ser_cities")
    ctx = Cendry(client=firestore_client)

    city = AliasedCity(display_name="SF", state="CA", population=870_000, id="sf-alias")
    ctx.save(city)

    fetched = ctx.get(AliasedCity, "sf-alias")
    assert fetched.display_name == "SF"

    # Verify Firestore stored the alias
    raw = firestore_client.collection("test_ser_cities").document("sf-alias").get().to_dict()
    assert "displayName" in raw
    assert "display_name" not in raw


def test_save_and_get_with_nested_map(firestore_client, clean_collection):
    clean_collection("test_ser_cities")
    ctx = Cendry(client=firestore_client)

    city = AliasedCity(
        display_name="SF",
        state="CA",
        population=870_000,
        mayor=Mayor(name="London Breed", since=2018),
        id="sf-map",
    )
    ctx.save(city)

    fetched = ctx.get(AliasedCity, "sf-map")
    assert fetched.mayor is not None
    assert fetched.mayor.name == "London Breed"
    assert fetched.mayor.since == 2018


def test_save_and_get_with_enum(firestore_client, clean_collection):
    clean_collection("test_ser_cities")
    ctx = Cendry(client=firestore_client)

    city = AliasedCity(
        display_name="SF", state="CA", population=870_000, status=Status.ACTIVE, id="sf-enum"
    )
    ctx.save(city)

    fetched = ctx.get(AliasedCity, "sf-enum")
    assert fetched.status == Status.ACTIVE


def test_to_dict_and_from_dict_roundtrip():
    city = AliasedCity(display_name="SF", state="CA", population=870_000, id="rt")

    data = to_dict(city, by_alias=True)
    assert "displayName" in data

    restored = from_dict(AliasedCity, data, by_alias=True, doc_id="rt")
    assert restored.display_name == "SF"


def test_custom_type_handler(firestore_client, clean_collection):
    class Money:
        def __init__(self, amount: int, currency: str) -> None:
            self.amount = amount
            self.currency = currency

    class MoneyHandler(BaseTypeHandler):
        def serialize(self, value: Money) -> dict[str, int | str]:
            return {"amount": value.amount, "currency": value.currency}

        def deserialize(self, value: dict[str, int | str]) -> Money:
            return Money(amount=value["amount"], currency=value["currency"])  # type: ignore[arg-type]

    registry = TypeRegistry()
    registry.register(Money, handler=MoneyHandler())

    # Can't define a model with Money in the default registry at module level,
    # so test via to_dict/from_dict with custom registry
    from cendry.serialize import serialize_update_value

    result = serialize_update_value(Money(100, "USD"), registry=registry)
    assert result == {"amount": 100, "currency": "USD"}
