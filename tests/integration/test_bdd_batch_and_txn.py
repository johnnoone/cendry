"""BDD integration tests for batch writes and transactions."""

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from cendry import Cendry, Field, Model

FEATURES = "features"


class City(Model, collection="bdd_batch_cities"):
    name: Field[str]
    population: Field[int]


@scenario(f"{FEATURES}/batch_and_transactions.feature", "Save many documents atomically")
def test_save_many():
    pass


@scenario(f"{FEATURES}/batch_and_transactions.feature", "Delete many documents")
def test_delete_many():
    pass


@scenario(f"{FEATURES}/batch_and_transactions.feature", "Batch with mixed operations")
def test_batch_mixed():
    pass


@scenario(
    f"{FEATURES}/batch_and_transactions.feature",
    "Transaction transfers population atomically",
)
def test_transaction_transfer():
    pass


@scenario(f"{FEATURES}/batch_and_transactions.feature", "Transaction rolls back on exception")
def test_transaction_rollback():
    pass


# --- Given ---


@given(
    "a Cendry context connected to the emulator",
    target_fixture="ctx_state",
)
def cendry_context(firestore_client, clean_collection):
    clean_collection("bdd_batch_cities")
    return {"ctx": Cendry(client=firestore_client)}


@given("2 saved cities", target_fixture="ctx_state")
def two_cities(firestore_client, clean_collection):
    clean_collection("bdd_batch_cities")
    ctx = Cendry(client=firestore_client)
    c1 = City(name="A", population=1, id="a")
    c2 = City(name="B", population=2, id="b")
    ctx.save_many([c1, c2])
    return {"ctx": ctx, "instances": [c1, c2]}


@given(
    parsers.parse('a saved City "{doc_id}" and a saved City "{doc_id2}"'),
    target_fixture="ctx_state",
)
def two_named_cities(firestore_client, clean_collection, doc_id: str, doc_id2: str):
    clean_collection("bdd_batch_cities")
    ctx = Cendry(client=firestore_client)
    ctx.save(City(name=doc_id, population=1, id=doc_id))
    ctx.save(City(name=doc_id2, population=2, id=doc_id2))
    return {"ctx": ctx}


@given(
    parsers.parse('a saved City "{doc_id}" with population {pop:d}'),
    target_fixture="ctx_state",
)
def saved_city(firestore_client, clean_collection, doc_id: str, pop: int):
    clean_collection("bdd_batch_cities")
    ctx = Cendry(client=firestore_client)
    ctx.save(City(name=doc_id, population=pop, id=doc_id))
    return {"ctx": ctx}


# --- When ---


@when(
    parsers.parse("I save {count:d} cities with save_many"),
    target_fixture="ctx_state",
)
def save_many(ctx_state, count: int):
    ctx = ctx_state["ctx"]
    cities = [City(name=f"city-{i}", population=i, id=f"city-{i}") for i in range(count)]
    ctx.save_many(cities)
    ctx_state["count"] = count
    return ctx_state


@when("I delete them with delete_many", target_fixture="ctx_state")
def delete_many(ctx_state):
    ctx_state["ctx"].delete_many(ctx_state["instances"])
    return ctx_state


@when(
    parsers.parse('I batch-save a new City "{new_id}" and batch-delete "{del_id}"'),
    target_fixture="ctx_state",
)
def batch_mixed(ctx_state, new_id: str, del_id: str):
    ctx = ctx_state["ctx"]
    with ctx.batch() as batch:
        batch.save(City(name=new_id, population=99, id=new_id))
        batch.delete(City, del_id)
    return ctx_state


@when(
    parsers.parse(
        'I transfer {amount:d} population from "{from_id}" to "{to_id}" in a transaction'
    ),
    target_fixture="ctx_state",
)
def transfer(ctx_state, amount: int, from_id: str, to_id: str):
    ctx = ctx_state["ctx"]

    def _transfer(txn):
        src = txn.get(City, from_id)
        dst = txn.get(City, to_id)
        txn.update(src, {"population": src.population - amount})
        txn.update(dst, {"population": dst.population + amount})

    ctx.transaction(_transfer)
    return ctx_state


@when(
    "a transaction raises an exception after queuing an update",
    target_fixture="ctx_state",
)
def txn_exception(ctx_state):
    ctx = ctx_state["ctx"]
    with pytest.raises(ValueError, match="abort"):  # noqa: PT012, SIM117
        with ctx.transaction() as txn:
            txn.update(City, "SF", {"population": 999})
            raise ValueError("abort")
    return ctx_state


# --- Then ---


@then(parsers.parse("all {count:d} cities are retrievable"))
def check_all_retrievable(ctx_state, count: int):
    ctx = ctx_state["ctx"]
    cities = ctx.select(City).to_list()
    assert len(cities) == count


@then("none of them are retrievable")
def check_none_retrievable(ctx_state):
    assert ctx_state["ctx"].select(City).to_list() == []


@then(parsers.parse('"{doc_id}" exists'))
def check_exists(ctx_state, doc_id: str):
    assert ctx_state["ctx"].find(City, doc_id) is not None


@then(parsers.parse('"{doc_id}" does not exist'))
def check_not_exists(ctx_state, doc_id: str):
    assert ctx_state["ctx"].find(City, doc_id) is None


@then(parsers.parse('"{doc_id}" has population {pop:d}'))
def check_population(ctx_state, doc_id: str, pop: int):
    city = ctx_state["ctx"].get(City, doc_id)
    assert city.population == pop


@then(parsers.parse('"{doc_id}" still has population {pop:d}'))
def check_unchanged(ctx_state, doc_id: str, pop: int):
    city = ctx_state["ctx"].get(City, doc_id)
    assert city.population == pop
