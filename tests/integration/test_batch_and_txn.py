"""Integration tests for batch writes and transactions against the Firestore emulator."""

import pytest

from cendry import Cendry, Field, Model


class City(Model, collection="test_batch_cities"):
    name: Field[str]
    population: Field[int]


# --- batch ---


def test_save_many(firestore_client, clean_collection):
    clean_collection("test_batch_cities")
    ctx = Cendry(client=firestore_client)

    cities = [
        City(name="A", population=1, id="a"),
        City(name="B", population=2, id="b"),
        City(name="C", population=3, id="c"),
    ]
    ctx.save_many(cities)

    fetched = ctx.select(City).to_list()
    assert len(fetched) == 3


def test_delete_many(firestore_client, clean_collection):
    clean_collection("test_batch_cities")
    ctx = Cendry(client=firestore_client)

    cities = [
        City(name="X", population=1, id="x"),
        City(name="Y", population=2, id="y"),
    ]
    ctx.save_many(cities)
    ctx.delete_many(cities)

    assert ctx.select(City).to_list() == []


def test_batch_mixed_operations(firestore_client, clean_collection):
    clean_collection("test_batch_cities")
    ctx = Cendry(client=firestore_client)

    ctx.save(City(name="Keep", population=100, id="keep"))
    ctx.save(City(name="Remove", population=0, id="remove"))

    with ctx.batch() as batch:
        batch.save(City(name="New", population=50, id="new"))
        batch.delete(City, "remove")

    assert ctx.find(City, "new") is not None
    assert ctx.find(City, "remove") is None
    assert ctx.find(City, "keep") is not None


# --- transactions ---


def test_transaction_callback(firestore_client, clean_collection):
    clean_collection("test_batch_cities")
    ctx = Cendry(client=firestore_client)

    ctx.save(City(name="SF", population=1000, id="sf"))
    ctx.save(City(name="LA", population=2000, id="la"))

    def transfer(txn):
        sf = txn.get(City, "sf")
        la = txn.get(City, "la")
        txn.update(sf, {"population": sf.population - 100})
        txn.update(la, {"population": la.population + 100})

    ctx.transaction(transfer)

    sf = ctx.get(City, "sf")
    la = ctx.get(City, "la")
    assert sf.population == 900
    assert la.population == 2100


def test_transaction_context_manager(firestore_client, clean_collection):
    clean_collection("test_batch_cities")
    ctx = Cendry(client=firestore_client)

    ctx.save(City(name="TXN City", population=500, id="txn"))

    with ctx.transaction() as txn:
        city = txn.get(City, "txn")
        txn.update(city, {"population": city.population + 250})

    fetched = ctx.get(City, "txn")
    assert fetched.population == 750


def test_transaction_rollback_on_exception(firestore_client, clean_collection):
    clean_collection("test_batch_cities")
    ctx = Cendry(client=firestore_client)

    ctx.save(City(name="Rollback", population=100, id="rb"))

    with pytest.raises(ValueError, match="abort"):  # noqa: PT012, SIM117
        with ctx.transaction() as txn:
            txn.update(City, "rb", {"population": 999})
            raise ValueError("abort")

    # Value should be unchanged
    fetched = ctx.get(City, "rb")
    assert fetched.population == 100
