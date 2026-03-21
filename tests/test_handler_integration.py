"""Integration tests for type handler system with serialization."""

from unittest.mock import MagicMock

from cendry import Cendry, Field, Model
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
