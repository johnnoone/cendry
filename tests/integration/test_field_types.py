"""Integration tests for all supported Field[T] types — save, get, compare round-trip."""

import dataclasses
import datetime
import enum
from decimal import Decimal
from typing import TypedDict

from google.cloud.firestore_v1._helpers import GeoPoint

from cendry import Cendry, Field, Map, Model
from cendry import field as cendry_field
from cendry.types import BaseTypeHandler, register_type

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Color(enum.Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class Priority(enum.Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


# ---------------------------------------------------------------------------
# Maps
# ---------------------------------------------------------------------------


class Address(Map):
    street: Field[str]
    city: Field[str]
    zip_code: Field[str]


class Coordinate(Map):
    lat: Field[float]
    lng: Field[float]


# ---------------------------------------------------------------------------
# Structured types
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class Tag:
    key: str
    value: str


class Metadata(TypedDict):
    source: str
    version: int


# ---------------------------------------------------------------------------
# Custom types with handlers
# ---------------------------------------------------------------------------


class Money:
    def __init__(self, amount: int, currency: str) -> None:
        self.amount = amount
        self.currency = currency

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.amount == other.amount and self.currency == other.currency

    def __repr__(self) -> str:
        return f"Money({self.amount}, {self.currency!r})"


class MoneyHandler(BaseTypeHandler):
    def serialize(self, value: Money) -> dict[str, int | str]:
        return {"amount": value.amount, "currency": value.currency}

    def deserialize(self, value: dict[str, int | str]) -> Money:
        return Money(amount=int(value["amount"]), currency=str(value["currency"]))


# Dataclass needs a handler — Firestore cannot encode arbitrary Python objects
class TagHandler(BaseTypeHandler):
    def serialize(self, value: Tag) -> dict[str, str]:
        return {"key": value.key, "value": value.value}

    def deserialize(self, value: dict[str, str]) -> Tag:
        return Tag(key=value["key"], value=value["value"])


# Register custom type handlers (Decimal, date, time have built-in handlers)
register_type(Money, handler=MoneyHandler())
register_type(Tag, handler=TagHandler())


# ---------------------------------------------------------------------------
# Models — one per test group to keep collections isolated
# ---------------------------------------------------------------------------

COLLECTION = "test_field_types"


class ScalarDoc(Model, collection=COLLECTION):
    str_val: Field[str]
    int_val: Field[int]
    float_val: Field[float]
    bool_val: Field[bool]
    bytes_val: Field[bytes]


class DecimalDoc(Model, collection=COLLECTION):
    value: Field[Decimal]


class DateTimeDoc(Model, collection=COLLECTION):
    dt_val: Field[datetime.datetime]
    date_val: Field[datetime.date]
    time_val: Field[datetime.time]


class GeoDoc(Model, collection=COLLECTION):
    location: Field[GeoPoint]


class OptionalDoc(Model, collection=COLLECTION):
    required: Field[str]
    optional_str: Field[str | None] = cendry_field(default=None)
    optional_int: Field[int | None] = cendry_field(default=None)


class ListDoc(Model, collection=COLLECTION):
    tags: Field[list[str]]
    numbers: Field[list[int]]


class SetDoc(Model, collection=COLLECTION):
    unique_tags: Field[set[str]]


class DictDoc(Model, collection=COLLECTION):
    metadata: Field[dict[str, int]]


class NestedContainerDoc(Model, collection=COLLECTION):
    matrix: Field[list[dict[str, int]]]
    tag_groups: Field[dict[str, list[str]]]


class EnumByValueDoc(Model, collection=COLLECTION):
    color: Field[Color]
    priority: Field[Priority]


class EnumByNameDoc(Model, collection=COLLECTION):
    color: Field[Color] = cendry_field(enum_by="name")


class MapDoc(Model, collection=COLLECTION):
    address: Field[Address]
    coord: Field[Coordinate | None] = cendry_field(default=None)


class NestedMapDoc(Model, collection=COLLECTION):
    addresses: Field[list[Address]]


class DataclassDoc(Model, collection=COLLECTION):
    tag: Field[Tag]


class TypedDictDoc(Model, collection=COLLECTION):
    meta: Field[Metadata]


class MoneyDoc(Model, collection=COLLECTION):
    price: Field[Money]
    prices: Field[list[Money]]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _roundtrip(ctx, doc, clean_collection):
    """Save a document, get it back, and return the fetched instance."""
    clean_collection(COLLECTION)
    ctx.save(doc)
    assert doc.id is not None
    return ctx.get(type(doc), doc.id)


# ---------------------------------------------------------------------------
# Scalar types
# ---------------------------------------------------------------------------


def test_str_int_float_bool_bytes(firestore_client, clean_collection):
    ctx = Cendry(client=firestore_client)
    original = ScalarDoc(
        str_val="hello",
        int_val=42,
        float_val=3.14,
        bool_val=True,
        bytes_val=b"\x00\x01\x02\xff",
    )
    fetched = _roundtrip(ctx, original, clean_collection)

    assert fetched.str_val == "hello"
    assert fetched.int_val == 42
    assert fetched.float_val == 3.14
    assert fetched.bool_val is True
    assert fetched.bytes_val == b"\x00\x01\x02\xff"


def test_decimal(firestore_client, clean_collection):
    ctx = Cendry(client=firestore_client)
    original = DecimalDoc(value=Decimal("123.456"))
    fetched = _roundtrip(ctx, original, clean_collection)

    # Stored as string in Firestore — lossless round-trip
    assert fetched.value == Decimal("123.456")

    # Verify raw storage is a string
    raw = firestore_client.collection(COLLECTION).document(original.id).get().to_dict()
    assert raw["value"] == "123.456"


def test_datetime(firestore_client, clean_collection):
    ctx = Cendry(client=firestore_client)
    now = datetime.datetime.now(tz=datetime.UTC)
    today = now.date()
    current_time = now.time()
    original = DateTimeDoc(dt_val=now, date_val=today, time_val=current_time)
    fetched = _roundtrip(ctx, original, clean_collection)

    # datetime round-trips with microsecond precision at best
    assert abs((fetched.dt_val - now).total_seconds()) < 1
    # date stored as datetime at midnight UTC — exact round-trip
    assert fetched.date_val == today
    # time stored as datetime on 1970-01-01 UTC — microseconds may be truncated
    assert fetched.time_val.hour == current_time.hour
    assert fetched.time_val.minute == current_time.minute
    assert fetched.time_val.second == current_time.second


def test_geopoint(firestore_client, clean_collection):
    ctx = Cendry(client=firestore_client)
    location = GeoPoint(latitude=37.7749, longitude=-122.4194)
    original = GeoDoc(location=location)
    fetched = _roundtrip(ctx, original, clean_collection)

    assert fetched.location.latitude == location.latitude
    assert fetched.location.longitude == location.longitude


# ---------------------------------------------------------------------------
# Optional types
# ---------------------------------------------------------------------------


def test_optional_none(firestore_client, clean_collection):
    ctx = Cendry(client=firestore_client)
    original = OptionalDoc(required="present")
    fetched = _roundtrip(ctx, original, clean_collection)

    assert fetched.required == "present"
    assert fetched.optional_str is None
    assert fetched.optional_int is None


def test_optional_with_value(firestore_client, clean_collection):
    ctx = Cendry(client=firestore_client)
    original = OptionalDoc(required="present", optional_str="hello", optional_int=42)
    fetched = _roundtrip(ctx, original, clean_collection)

    assert fetched.optional_str == "hello"
    assert fetched.optional_int == 42


# ---------------------------------------------------------------------------
# Container types
# ---------------------------------------------------------------------------


def test_list(firestore_client, clean_collection):
    ctx = Cendry(client=firestore_client)
    original = ListDoc(tags=["python", "firestore"], numbers=[1, 2, 3])
    fetched = _roundtrip(ctx, original, clean_collection)

    assert fetched.tags == ["python", "firestore"]
    assert fetched.numbers == [1, 2, 3]


def test_set(firestore_client, clean_collection):
    ctx = Cendry(client=firestore_client)
    original = SetDoc(unique_tags={"alpha", "beta", "gamma"})
    fetched = _roundtrip(ctx, original, clean_collection)

    assert fetched.unique_tags == {"alpha", "beta", "gamma"}


def test_dict(firestore_client, clean_collection):
    ctx = Cendry(client=firestore_client)
    original = DictDoc(metadata={"views": 100, "likes": 42})
    fetched = _roundtrip(ctx, original, clean_collection)

    assert fetched.metadata == {"views": 100, "likes": 42}


def test_nested_containers(firestore_client, clean_collection):
    ctx = Cendry(client=firestore_client)
    original = NestedContainerDoc(
        matrix=[{"a": 1, "b": 2}, {"c": 3}],
        tag_groups={"langs": ["python", "go"], "tools": ["firestore"]},
    )
    fetched = _roundtrip(ctx, original, clean_collection)

    assert fetched.matrix == [{"a": 1, "b": 2}, {"c": 3}]
    assert fetched.tag_groups == {"langs": ["python", "go"], "tools": ["firestore"]}


# ---------------------------------------------------------------------------
# Enum types
# ---------------------------------------------------------------------------


def test_enum_by_value(firestore_client, clean_collection):
    ctx = Cendry(client=firestore_client)
    original = EnumByValueDoc(color=Color.RED, priority=Priority.HIGH)
    fetched = _roundtrip(ctx, original, clean_collection)

    assert fetched.color is Color.RED
    assert fetched.priority is Priority.HIGH

    # Verify raw storage
    raw = firestore_client.collection(COLLECTION).document(original.id).get().to_dict()
    assert raw["color"] == "red"
    assert raw["priority"] == 3


def test_enum_by_name(firestore_client, clean_collection):
    ctx = Cendry(client=firestore_client)
    original = EnumByNameDoc(color=Color.GREEN)
    fetched = _roundtrip(ctx, original, clean_collection)

    assert fetched.color is Color.GREEN

    # Verify raw storage uses the name
    raw = firestore_client.collection(COLLECTION).document(original.id).get().to_dict()
    assert raw["color"] == "GREEN"


# ---------------------------------------------------------------------------
# Map types (embedded documents)
# ---------------------------------------------------------------------------


def test_map(firestore_client, clean_collection):
    ctx = Cendry(client=firestore_client)
    original = MapDoc(
        address=Address(street="123 Main St", city="Springfield", zip_code="62701"),
        coord=Coordinate(lat=39.7817, lng=-89.6501),
    )
    fetched = _roundtrip(ctx, original, clean_collection)

    assert fetched.address.street == "123 Main St"
    assert fetched.address.city == "Springfield"
    assert fetched.address.zip_code == "62701"
    assert fetched.coord is not None
    assert fetched.coord.lat == 39.7817
    assert fetched.coord.lng == -89.6501


def test_map_optional_none(firestore_client, clean_collection):
    ctx = Cendry(client=firestore_client)
    original = MapDoc(
        address=Address(street="456 Elm St", city="Shelbyville", zip_code="62565"),
    )
    fetched = _roundtrip(ctx, original, clean_collection)

    assert fetched.address.street == "456 Elm St"
    assert fetched.coord is None


def test_list_of_maps(firestore_client, clean_collection):
    ctx = Cendry(client=firestore_client)
    addrs = [
        Address(street="1 First St", city="A", zip_code="00001"),
        Address(street="2 Second St", city="B", zip_code="00002"),
    ]
    original = NestedMapDoc(addresses=addrs)
    fetched = _roundtrip(ctx, original, clean_collection)

    assert len(fetched.addresses) == 2
    assert fetched.addresses[0].street == "1 First St"
    assert fetched.addresses[1].city == "B"


# ---------------------------------------------------------------------------
# Structured types (dataclass, TypedDict)
# ---------------------------------------------------------------------------


def test_dataclass_field(firestore_client, clean_collection):
    ctx = Cendry(client=firestore_client)
    original = DataclassDoc(tag=Tag(key="env", value="prod"))
    fetched = _roundtrip(ctx, original, clean_collection)

    assert fetched.tag == Tag(key="env", value="prod")


def test_typeddict_field(firestore_client, clean_collection):
    ctx = Cendry(client=firestore_client)
    original = TypedDictDoc(meta={"source": "api", "version": 3})
    fetched = _roundtrip(ctx, original, clean_collection)

    assert fetched.meta == {"source": "api", "version": 3}


# ---------------------------------------------------------------------------
# Custom type handler
# ---------------------------------------------------------------------------


def test_custom_type_handler(firestore_client, clean_collection):
    ctx = Cendry(client=firestore_client)
    original = MoneyDoc(
        price=Money(1999, "USD"),
        prices=[Money(999, "EUR"), Money(500, "GBP")],
    )
    fetched = _roundtrip(ctx, original, clean_collection)

    assert fetched.price == Money(1999, "USD")
    assert fetched.prices == [Money(999, "EUR"), Money(500, "GBP")]

    # Verify raw storage
    raw = firestore_client.collection(COLLECTION).document(original.id).get().to_dict()
    assert raw["price"] == {"amount": 1999, "currency": "USD"}
    assert raw["prices"] == [
        {"amount": 999, "currency": "EUR"},
        {"amount": 500, "currency": "GBP"},
    ]
