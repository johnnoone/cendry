"""Integration tests for CRUD operations against the Firestore emulator."""

import pytest

from cendry import (
    Cendry,
    DocumentAlreadyExistsError,
    DocumentNotFoundError,
    Field,
    Model,
)
from cendry.metadata import get_metadata


class City(Model, collection="test_cities"):
    name: Field[str]
    state: Field[str]
    population: Field[int]


# --- save ---


def test_save_and_get(firestore_client, clean_collection):
    clean_collection("test_cities")
    ctx = Cendry(client=firestore_client)

    city = City(name="San Francisco", state="CA", population=870_000)
    doc_id = ctx.save(city)

    assert city.id is not None
    assert doc_id == city.id

    fetched = ctx.get(City, city.id)
    assert fetched.name == "San Francisco"
    assert fetched.state == "CA"
    assert fetched.population == 870_000


def test_save_overwrites(firestore_client, clean_collection):
    clean_collection("test_cities")
    ctx = Cendry(client=firestore_client)

    city = City(name="SF", state="CA", population=870_000, id="overwrite-test")
    ctx.save(city)

    city.population = 900_000  # type: ignore[assignment]
    ctx.save(city)

    fetched = ctx.get(City, "overwrite-test")
    assert fetched.population == 900_000


# --- create ---


def test_create_and_duplicate_raises(firestore_client, clean_collection):
    clean_collection("test_cities")
    ctx = Cendry(client=firestore_client)

    city = City(name="LA", state="CA", population=3_900_000, id="create-test")
    ctx.create(city)

    fetched = ctx.get(City, "create-test")
    assert fetched.name == "LA"

    duplicate = City(name="LA2", state="CA", population=0, id="create-test")
    with pytest.raises(DocumentAlreadyExistsError):
        ctx.create(duplicate)


# --- update ---


def test_update_partial(firestore_client, clean_collection):
    clean_collection("test_cities")
    ctx = Cendry(client=firestore_client)

    city = City(name="NYC", state="NY", population=8_300_000, id="update-test")
    ctx.save(city)

    ctx.update(city, {"population": 8_400_000})

    fetched = ctx.get(City, "update-test")
    assert fetched.population == 8_400_000
    assert fetched.name == "NYC"  # unchanged


def test_update_by_class_and_id(firestore_client, clean_collection):
    clean_collection("test_cities")
    ctx = Cendry(client=firestore_client)

    ctx.save(City(name="Chicago", state="IL", population=2_700_000, id="chi"))
    ctx.update(City, "chi", {"population": 2_800_000})

    fetched = ctx.get(City, "chi")
    assert fetched.population == 2_800_000


def test_update_missing_raises(firestore_client, clean_collection):
    clean_collection("test_cities")
    ctx = Cendry(client=firestore_client)

    with pytest.raises(DocumentNotFoundError):
        ctx.update(City, "nonexistent", {"population": 0})


# --- delete ---


def test_delete_by_instance(firestore_client, clean_collection):
    clean_collection("test_cities")
    ctx = Cendry(client=firestore_client)

    city = City(name="Delete Me", state="XX", population=0, id="delete-test")
    ctx.save(city)
    ctx.delete(city)

    assert ctx.find(City, "delete-test") is None


def test_delete_by_class_and_id(firestore_client, clean_collection):
    clean_collection("test_cities")
    ctx = Cendry(client=firestore_client)

    ctx.save(City(name="Gone", state="XX", population=0, id="del2"))
    ctx.delete(City, "del2")

    assert ctx.find(City, "del2") is None


# --- find ---


def test_find_returns_none(firestore_client, clean_collection):
    clean_collection("test_cities")
    ctx = Cendry(client=firestore_client)

    assert ctx.find(City, "does-not-exist") is None


# --- refresh ---


def test_refresh_updates_instance(firestore_client, clean_collection):
    clean_collection("test_cities")
    ctx = Cendry(client=firestore_client)

    city = City(name="Refresh City", state="XX", population=100, id="refresh-test")
    ctx.save(city)

    # Update directly via Firestore, bypassing Cendry
    firestore_client.collection("test_cities").document("refresh-test").update({"population": 999})

    ctx.refresh(city)
    assert city.population == 999


# --- metadata ---


def test_metadata_populated_on_get(firestore_client, clean_collection):
    clean_collection("test_cities")
    ctx = Cendry(client=firestore_client)

    ctx.save(City(name="Meta City", state="XX", population=1, id="meta-test"))
    city = ctx.get(City, "meta-test")

    meta = get_metadata(city)
    assert meta.update_time is not None
    assert meta.create_time is not None


def test_metadata_populated_on_save(firestore_client, clean_collection):
    clean_collection("test_cities")
    ctx = Cendry(client=firestore_client)

    city = City(name="Meta Save", state="XX", population=1, id="meta-save")
    ctx.save(city)

    meta = get_metadata(city)
    assert meta.update_time is not None
