"""Integration tests for type handler system with serialization."""

import enum
from unittest.mock import MagicMock

from cendry import Cendry, Field, Model
from cendry import field as cendry_field
from cendry.serialize import deserialize, from_dict, to_dict
from cendry.types import BaseTypeHandler, default_registry
from tests.conftest import make_mock_document


class Money:
    def __init__(self, amount: int, currency: str) -> None:
        self.amount = amount
        self.currency = currency


class MoneyHandler(BaseTypeHandler):
    def serialize(self, value: Money) -> dict[str, int | str]:
        return {"amount": value.amount, "currency": value.currency}

    def deserialize(self, value: dict[str, int | str]) -> Money:
        return Money(amount=value["amount"], currency=value["currency"])


# Register globally for these tests
default_registry.register(Money, handler=MoneyHandler())


class Invoice(Model, collection="invoices"):
    title: Field[str]
    total: Field[Money]


def test_deserialize_with_handler():
    result = deserialize(
        Invoice,
        "inv1",
        {
            "title": "Test",
            "total": {"amount": 100, "currency": "USD"},
        },
    )
    assert isinstance(result.total, Money)
    assert result.total.amount == 100
    assert result.total.currency == "USD"


def test_to_dict_with_handler():
    invoice = Invoice(title="Test", total=Money(amount=100, currency="USD"))
    result = to_dict(invoice)
    assert result["total"] == {"amount": 100, "currency": "USD"}


def test_from_dict_with_handler():
    invoice = from_dict(
        Invoice,
        {
            "title": "Test",
            "total": {"amount": 100, "currency": "USD"},
        },
    )
    assert isinstance(invoice.total, Money)
    assert invoice.total.amount == 100


def test_context_get_with_handler(mock_firestore_client: MagicMock):
    doc = make_mock_document(
        "inv1",
        {
            "title": "Test",
            "total": {"amount": 100, "currency": "USD"},
        },
    )
    mock_firestore_client.collection.return_value.document.return_value.get.return_value = doc

    ctx = Cendry(client=mock_firestore_client)
    invoice = ctx.get(Invoice, "inv1")
    assert isinstance(invoice.total, Money)
    assert invoice.total.amount == 100


def test_handler_with_optional_field():
    class Order(Model, collection="orders"):
        title: Field[str]
        total: Field[Money | None]

    result = deserialize(Order, "o1", {"title": "Test", "total": None})
    assert result.total is None

    result2 = deserialize(
        Order,
        "o2",
        {
            "title": "Test",
            "total": {"amount": 50, "currency": "EUR"},
        },
    )
    assert isinstance(result2.total, Money)
    assert result2.total.amount == 50


# --- Container type handlers ---


class Cart(Model, collection="carts"):
    title: Field[str]
    items: Field[list[Money]]


def test_deserialize_list_of_handler_type():
    result = deserialize(Cart, "c1", {
        "title": "Cart",
        "items": [
            {"amount": 10, "currency": "USD"},
            {"amount": 20, "currency": "EUR"},
        ],
    })
    assert len(result.items) == 2
    assert all(isinstance(m, Money) for m in result.items)
    assert result.items[0].amount == 10
    assert result.items[1].currency == "EUR"


def test_to_dict_list_of_handler_type():
    cart = Cart(title="Cart", items=[Money(10, "USD"), Money(20, "EUR")])
    result = to_dict(cart)
    assert result["items"] == [
        {"amount": 10, "currency": "USD"},
        {"amount": 20, "currency": "EUR"},
    ]


class Ledger(Model, collection="ledgers"):
    title: Field[str]
    accounts: Field[dict[str, Money]]


def test_deserialize_dict_of_handler_type():
    result = deserialize(Ledger, "l1", {
        "title": "Ledger",
        "accounts": {
            "checking": {"amount": 100, "currency": "USD"},
            "savings": {"amount": 200, "currency": "EUR"},
        },
    })
    assert isinstance(result.accounts["checking"], Money)
    assert result.accounts["savings"].amount == 200


def test_to_dict_dict_of_handler_type():
    ledger = Ledger(
        title="Ledger",
        accounts={
            "checking": Money(100, "USD"),
            "savings": Money(200, "EUR"),
        },
    )
    result = to_dict(ledger)
    assert result["accounts"]["checking"] == {"amount": 100, "currency": "USD"}


# --- Enum conversion ---


class Status(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Role(enum.Enum):
    ADMIN = "admin"
    USER = "user"


class UserByValue(Model, collection="users_by_value"):
    name: Field[str]
    status: Field[Status]


class UserByName(Model, collection="users_by_name"):
    name: Field[str]
    role: Field[Role] = cendry_field(enum_by="name")


def test_enum_deserialize_by_value():
    result = deserialize(UserByValue, "u1", {"name": "Alice", "status": "active"})
    assert result.status is Status.ACTIVE


def test_enum_deserialize_by_name():
    result = deserialize(UserByName, "u1", {"name": "Alice", "role": "ADMIN"})
    assert result.role is Role.ADMIN


def test_enum_serialize_by_value():
    user = UserByValue(name="Alice", status=Status.INACTIVE)
    result = to_dict(user)
    assert result["status"] == "inactive"


def test_enum_serialize_by_name():
    user = UserByName(name="Alice", role=Role.USER)
    result = to_dict(user)
    assert result["role"] == "USER"


def test_enum_from_dict():
    user = from_dict(UserByValue, {"name": "Alice", "status": "active"})
    assert user.status is Status.ACTIVE


def test_enum_optional_none():
    class OptUser(Model, collection="opt_users"):
        name: Field[str]
        status: Field[Status | None] = cendry_field(default=None)

    result = deserialize(OptUser, "u1", {"name": "Alice"})
    assert result.status is None
