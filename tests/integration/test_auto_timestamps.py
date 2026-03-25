"""Integration tests for auto_now / auto_now_add against the Firestore emulator."""

import datetime

from cendry import Cendry, Field, Model, field


class TimestampedDoc(Model, collection="ts_docs"):
    title: Field[str]
    created_at: Field[datetime.datetime | None] = field(auto_now_add=True)
    updated_at: Field[datetime.datetime | None] = field(auto_now=True)


def test_save_fills_auto_timestamps(firestore_client, clean_collection):
    clean_collection("ts_docs")
    ctx = Cendry(client=firestore_client)
    doc = TimestampedDoc(title="hello")
    assert doc.created_at is None
    assert doc.updated_at is None

    ctx.save(doc)

    assert doc.created_at is not None
    assert doc.updated_at is not None
    assert isinstance(doc.created_at, datetime.datetime)
    assert isinstance(doc.updated_at, datetime.datetime)


def test_save_auto_now_add_preserves_on_second_save(firestore_client, clean_collection):
    clean_collection("ts_docs")
    ctx = Cendry(client=firestore_client)
    doc = TimestampedDoc(title="hello")
    ctx.save(doc)
    first_created = doc.created_at
    first_updated = doc.updated_at

    doc.title = "updated"
    ctx.save(doc)

    assert doc.created_at == first_created  # auto_now_add: preserved
    assert doc.updated_at != first_updated  # auto_now: overwritten


def test_create_fills_auto_timestamps(firestore_client, clean_collection):
    clean_collection("ts_docs")
    ctx = Cendry(client=firestore_client)
    doc = TimestampedDoc(title="hello")
    ctx.create(doc)

    assert doc.created_at is not None
    assert doc.updated_at is not None


def test_roundtrip_timestamps_persist(firestore_client, clean_collection):
    clean_collection("ts_docs")
    ctx = Cendry(client=firestore_client)
    doc = TimestampedDoc(title="persist")
    ctx.save(doc)

    fetched = ctx.get(TimestampedDoc, doc.id)
    assert fetched.created_at is not None
    assert fetched.updated_at is not None
