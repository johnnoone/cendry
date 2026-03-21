import datetime
from decimal import Decimal

import pytest
from google.cloud.firestore_v1._helpers import GeoPoint
from google.cloud.firestore_v1.document import DocumentReference

from cendry.types import TypeRegistry


@pytest.fixture
def registry() -> TypeRegistry:
    return TypeRegistry()


# --- Scalars ---


def test_str_is_valid(registry: TypeRegistry):
    registry.validate("name", str, "TestModel")


def test_int_is_valid(registry: TypeRegistry):
    registry.validate("count", int, "TestModel")


def test_float_is_valid(registry: TypeRegistry):
    registry.validate("score", float, "TestModel")


def test_bool_is_valid(registry: TypeRegistry):
    registry.validate("active", bool, "TestModel")


def test_bytes_is_valid(registry: TypeRegistry):
    registry.validate("data", bytes, "TestModel")


def test_decimal_is_valid(registry: TypeRegistry):
    registry.validate("price", Decimal, "TestModel")


def test_datetime_is_valid(registry: TypeRegistry):
    registry.validate("created", datetime.datetime, "TestModel")


def test_complex_is_invalid(registry: TypeRegistry):
    with pytest.raises(TypeError, match="complex"):
        registry.validate("val", complex, "TestModel")


def test_object_is_invalid(registry: TypeRegistry):
    with pytest.raises(TypeError, match="object"):
        registry.validate("val", object, "TestModel")


# --- Firestore SDK ---


def test_geopoint_is_valid(registry: TypeRegistry):
    registry.validate("location", GeoPoint, "TestModel")


def test_document_reference_is_valid(registry: TypeRegistry):
    registry.validate("ref", DocumentReference, "TestModel")
