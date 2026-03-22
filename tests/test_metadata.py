import datetime
import gc

import pytest

from cendry import CendryError
from cendry.metadata import (
    DocumentMetadata,
    _clear_metadata,
    _set_metadata,
    get_metadata,
)
from tests.conftest import SF_DATA, City


def test_get_metadata_untracked_raises():
    city = City(**SF_DATA, id="SF")
    with pytest.raises(CendryError, match="No metadata for this instance"):
        get_metadata(city)


def test_set_and_get_metadata():
    city = City(**SF_DATA, id="SF")
    now = datetime.datetime.now(tz=datetime.UTC)
    _set_metadata(city, update_time=now, create_time=now)

    meta = get_metadata(city)
    assert meta.update_time == now
    assert meta.create_time == now


def test_set_metadata_updates_existing():
    city = City(**SF_DATA, id="SF")
    t1 = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
    t2 = datetime.datetime(2026, 6, 1, tzinfo=datetime.UTC)

    _set_metadata(city, update_time=t1, create_time=t1)
    _set_metadata(city, update_time=t2)

    meta = get_metadata(city)
    assert meta.update_time == t2
    assert meta.create_time == t1  # not overwritten


def test_clear_metadata():
    city = City(**SF_DATA, id="SF")
    _set_metadata(city, update_time=datetime.datetime.now(tz=datetime.UTC))
    _clear_metadata(city)

    with pytest.raises(CendryError, match="No metadata"):
        get_metadata(city)


def test_clear_metadata_noop_on_untracked():
    city = City(**SF_DATA, id="SF")
    _clear_metadata(city)  # should not raise


def test_weakref_cleanup():
    city = City(**SF_DATA, id="SF")
    _set_metadata(city, update_time=datetime.datetime.now(tz=datetime.UTC))

    # Verify it's tracked
    get_metadata(city)

    # Drop reference — metadata should be GC'd
    city_id = id(city)
    del city
    gc.collect()

    # Can't directly test the store is empty without the instance,
    # but we verify no error on a new instance with same data
    city2 = City(**SF_DATA, id="SF")
    with pytest.raises(CendryError, match="No metadata"):
        get_metadata(city2)


def test_document_metadata_defaults():
    meta = DocumentMetadata()
    assert meta.update_time is None
    assert meta.create_time is None
