"""Integration tests for Datastore backend against the Datastore emulator."""

import pytest

from cendry import (
    Cendry,
    CendryError,
    DocumentAlreadyExistsError,
    DocumentNotFoundError,
    Field,
    Model,
)
from cendry.backends.datastore import DatastoreBackend


class DsCity(Model, collection="ds_test_cities"):
    name: Field[str]
    state: Field[str]
    population: Field[int]


class DsBatchCity(Model, collection="ds_test_batch_cities"):
    name: Field[str]
    population: Field[int]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def ds_ctx(datastore_client, clean_datastore):
    """Cendry context backed by Datastore, with cleanup registered."""
    clean_datastore("ds_test_cities")
    backend = DatastoreBackend(client=datastore_client)
    return Cendry(backend=backend)


@pytest.fixture
def ds_batch_ctx(datastore_client, clean_datastore):
    """Cendry context for batch/txn tests."""
    clean_datastore("ds_test_batch_cities")
    backend = DatastoreBackend(client=datastore_client)
    return Cendry(backend=backend)


@pytest.fixture
def seeded_ds_ctx(datastore_client, clean_datastore):
    """Seed test data and return a Cendry context."""
    clean_datastore("ds_test_cities")
    backend = DatastoreBackend(client=datastore_client)
    ctx = Cendry(backend=backend)
    ctx.save_many(
        [
            DsCity(name="San Francisco", state="CA", population=870_000, id="SF"),
            DsCity(name="Los Angeles", state="CA", population=3_900_000, id="LA"),
            DsCity(name="New York", state="NY", population=8_300_000, id="NYC"),
            DsCity(name="Chicago", state="IL", population=2_700_000, id="CHI"),
        ]
    )
    return ctx


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def test_ds_save_and_get(ds_ctx):
    city = DsCity(name="San Francisco", state="CA", population=870_000)
    doc_id = ds_ctx.save(city)

    assert city.id is not None
    assert doc_id == city.id

    fetched = ds_ctx.get(DsCity, city.id)
    assert fetched.name == "San Francisco"
    assert fetched.state == "CA"
    assert fetched.population == 870_000


def test_ds_save_overwrites(ds_ctx):
    city = DsCity(name="SF", state="CA", population=870_000, id="overwrite-ds")
    ds_ctx.save(city)

    city.population = 900_000  # type: ignore[assignment]
    ds_ctx.save(city)

    fetched = ds_ctx.get(DsCity, "overwrite-ds")
    assert fetched.population == 900_000


def test_ds_create_and_duplicate_raises(ds_ctx):
    city = DsCity(name="LA", state="CA", population=3_900_000, id="create-ds")
    ds_ctx.create(city)

    fetched = ds_ctx.get(DsCity, "create-ds")
    assert fetched.name == "LA"

    duplicate = DsCity(name="LA2", state="CA", population=0, id="create-ds")
    with pytest.raises(DocumentAlreadyExistsError):
        ds_ctx.create(duplicate)


def test_ds_find_returns_none(ds_ctx):
    assert ds_ctx.find(DsCity, "does-not-exist") is None


def test_ds_update_partial(ds_ctx):
    city = DsCity(name="NYC", state="NY", population=8_300_000, id="update-ds")
    ds_ctx.save(city)

    ds_ctx.update(city, {"population": 8_400_000})

    fetched = ds_ctx.get(DsCity, "update-ds")
    assert fetched.population == 8_400_000
    assert fetched.name == "NYC"  # unchanged


def test_ds_update_missing_raises(ds_ctx):
    with pytest.raises(DocumentNotFoundError):
        ds_ctx.update(DsCity, "nonexistent", {"population": 0})


def test_ds_delete_by_instance(ds_ctx):
    city = DsCity(name="Delete Me", state="XX", population=0, id="delete-ds")
    ds_ctx.save(city)
    ds_ctx.delete(city)

    assert ds_ctx.find(DsCity, "delete-ds") is None


def test_ds_delete_by_class_and_id(ds_ctx):
    ds_ctx.save(DsCity(name="Gone", state="XX", population=0, id="del2-ds"))
    ds_ctx.delete(DsCity, "del2-ds")

    assert ds_ctx.find(DsCity, "del2-ds") is None


def test_ds_get_many(seeded_ds_ctx):
    cities = seeded_ds_ctx.get_many(DsCity, ["SF", "NYC"])
    assert len(cities) == 2
    names = {c.name for c in cities}
    assert "San Francisco" in names
    assert "New York" in names


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


def test_ds_select_all(seeded_ds_ctx):
    cities = seeded_ds_ctx.select(DsCity).to_list()
    assert len(cities) == 4


def test_ds_select_with_filter(seeded_ds_ctx):
    ca_cities = seeded_ds_ctx.select(DsCity, DsCity.state == "CA").to_list()
    assert len(ca_cities) == 2
    assert all(c.state == "CA" for c in ca_cities)


def test_ds_select_with_limit(seeded_ds_ctx):
    cities = seeded_ds_ctx.select(DsCity).limit(2).to_list()
    assert len(cities) == 2


def test_ds_query_first(seeded_ds_ctx):
    city = seeded_ds_ctx.select(DsCity, DsCity.state == "NY").first()
    assert city is not None
    assert city.name == "New York"


def test_ds_query_first_none(seeded_ds_ctx):
    city = seeded_ds_ctx.select(DsCity, DsCity.state == "TX").first()
    assert city is None


def test_ds_query_count(seeded_ds_ctx):
    n = seeded_ds_ctx.select(DsCity, DsCity.state == "CA").count()
    assert n == 2


def test_ds_query_order_by(seeded_ds_ctx):
    cities = seeded_ds_ctx.select(DsCity).order_by(DsCity.population.asc()).to_list()
    populations = [c.population for c in cities]
    assert populations == sorted(populations)


def test_ds_query_exists(seeded_ds_ctx):
    assert seeded_ds_ctx.select(DsCity, DsCity.state == "CA").exists()
    assert not seeded_ds_ctx.select(DsCity, DsCity.state == "TX").exists()


# ---------------------------------------------------------------------------
# Batch & Transaction
# ---------------------------------------------------------------------------


def test_ds_save_many(ds_batch_ctx):
    cities = [
        DsBatchCity(name="A", population=1, id="a"),
        DsBatchCity(name="B", population=2, id="b"),
        DsBatchCity(name="C", population=3, id="c"),
    ]
    ds_batch_ctx.save_many(cities)

    fetched = ds_batch_ctx.select(DsBatchCity).to_list()
    assert len(fetched) == 3


def test_ds_delete_many(ds_batch_ctx):
    cities = [
        DsBatchCity(name="X", population=1, id="x"),
        DsBatchCity(name="Y", population=2, id="y"),
    ]
    ds_batch_ctx.save_many(cities)
    ds_batch_ctx.delete_many(cities)

    assert ds_batch_ctx.select(DsBatchCity).to_list() == []


def test_ds_batch_mixed(ds_batch_ctx):
    ds_batch_ctx.save(DsBatchCity(name="Keep", population=100, id="keep"))
    ds_batch_ctx.save(DsBatchCity(name="Remove", population=0, id="remove"))

    with ds_batch_ctx.batch() as batch:
        batch.save(DsBatchCity(name="New", population=50, id="new"))
        batch.delete(DsBatchCity, "remove")

    assert ds_batch_ctx.find(DsBatchCity, "new") is not None
    assert ds_batch_ctx.find(DsBatchCity, "remove") is None
    assert ds_batch_ctx.find(DsBatchCity, "keep") is not None


def test_ds_transaction_context_manager(ds_batch_ctx):
    ds_batch_ctx.save(DsBatchCity(name="TXN City", population=500, id="txn"))

    with ds_batch_ctx.transaction() as txn:
        city = txn.get(DsBatchCity, "txn")
        txn.update(city, {"population": city.population + 250})  # type: ignore[operator]

    fetched = ds_batch_ctx.get(DsBatchCity, "txn")
    assert fetched.population == 750


# ---------------------------------------------------------------------------
# Unsupported features
# ---------------------------------------------------------------------------


def test_ds_collection_group_raises(ds_ctx):
    with pytest.raises(CendryError, match="Collection group"):
        ds_ctx.select_group(DsCity)


def test_ds_on_snapshot_raises(ds_ctx):
    with pytest.raises(CendryError, match="Real-time listeners"):
        ds_ctx.on_snapshot(DsCity, "some-id", lambda *a: None)
