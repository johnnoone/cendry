"""Integration tests for transaction read/write operations."""

import pytest

from cendry import Cendry, DocumentNotFoundError, Field, Model
from cendry.metadata import get_metadata


class City(Model, collection="test_txn_adv_cities"):
    name: Field[str]
    population: Field[int]


def test_transaction_get_and_find(firestore_client, clean_collection):
    clean_collection("test_txn_adv_cities")
    ctx = Cendry(client=firestore_client)
    ctx.save(City(name="SF", population=1000, id="sf"))

    with ctx.transaction() as txn:
        city = txn.get(City, "sf")
        assert city.name == "SF"

        found = txn.find(City, "sf")
        assert found is not None
        assert found.name == "SF"

        not_found = txn.find(City, "nope")
        assert not_found is None


def test_transaction_get_missing_raises(firestore_client, clean_collection):
    clean_collection("test_txn_adv_cities")
    ctx = Cendry(client=firestore_client)

    with pytest.raises(DocumentNotFoundError), ctx.transaction() as txn:
        txn.get(City, "nope")


def test_transaction_save_and_create(firestore_client, clean_collection):
    clean_collection("test_txn_adv_cities")
    ctx = Cendry(client=firestore_client)

    with ctx.transaction() as txn:
        txn.save(City(name="A", population=1, id="a"))
        txn.create(City(name="B", population=2, id="b"))

    assert ctx.get(City, "a").name == "A"
    assert ctx.get(City, "b").name == "B"


def test_transaction_delete(firestore_client, clean_collection):
    clean_collection("test_txn_adv_cities")
    ctx = Cendry(client=firestore_client)
    ctx.save(City(name="Gone", population=0, id="gone"))

    with ctx.transaction() as txn:
        txn.delete(City, "gone")

    assert ctx.find(City, "gone") is None


def test_transaction_callback_return_value(firestore_client, clean_collection):
    clean_collection("test_txn_adv_cities")
    ctx = Cendry(client=firestore_client)
    ctx.save(City(name="SF", population=1000, id="sf"))

    def read_pop(txn):
        city = txn.get(City, "sf")
        return city.population

    result = ctx.transaction(read_pop)
    assert result == 1000


def test_transaction_metadata_on_read(firestore_client, clean_collection):
    clean_collection("test_txn_adv_cities")
    ctx = Cendry(client=firestore_client)
    ctx.save(City(name="Meta", population=1, id="meta"))

    with ctx.transaction() as txn:
        city = txn.get(City, "meta")
        meta = get_metadata(city)
        assert meta.update_time is not None
