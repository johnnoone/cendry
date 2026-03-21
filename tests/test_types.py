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


# --- Optional ---


def test_optional_str_is_valid(registry: TypeRegistry):
    registry.validate("name", str | None, "TestModel")


def test_optional_complex_is_invalid(registry: TypeRegistry):
    with pytest.raises(TypeError, match="complex"):
        registry.validate("val", complex | None, "TestModel")


# --- Containers ---


def test_list_str_is_valid(registry: TypeRegistry):
    registry.validate("tags", list[str], "TestModel")


def test_list_complex_is_invalid(registry: TypeRegistry):
    with pytest.raises(TypeError, match="complex"):
        registry.validate("tags", list[complex], "TestModel")


def test_set_int_is_valid(registry: TypeRegistry):
    registry.validate("ids", set[int], "TestModel")


def test_tuple_str_int_is_valid(registry: TypeRegistry):
    registry.validate("pair", tuple[str, int], "TestModel")


def test_dict_str_int_is_valid(registry: TypeRegistry):
    registry.validate("data", dict[str, int], "TestModel")


def test_dict_int_key_is_invalid(registry: TypeRegistry):
    with pytest.raises(TypeError, match="dict keys must be str"):
        registry.validate("data", dict[int, str], "TestModel")


def test_nested_list_dict_is_valid(registry: TypeRegistry):
    registry.validate("items", list[dict[str, int]], "TestModel")


def test_nested_invalid_inner_type(registry: TypeRegistry):
    with pytest.raises(TypeError, match="complex"):
        registry.validate("items", list[dict[str, complex]], "TestModel")


def test_bare_list_is_valid(registry: TypeRegistry):
    registry.validate("items", list, "TestModel")


def test_bare_dict_is_valid(registry: TypeRegistry):
    registry.validate("data", dict, "TestModel")


# --- Structured types ---


def test_map_subclass_is_valid(registry: TypeRegistry):
    from cendry import Field, Map

    class Mayor(Map):
        name: Field[str]

    registry.validate("mayor", Mayor, "TestModel")


def test_dataclass_is_valid(registry: TypeRegistry):
    import dataclasses

    @dataclasses.dataclass
    class Point:
        x: float
        y: float

    registry.validate("location", Point, "TestModel")


def test_typeddict_is_valid(registry: TypeRegistry):
    from typing import TypedDict

    class Config(TypedDict):
        key: str
        value: int

    registry.validate("config", Config, "TestModel")


def test_model_is_invalid(registry: TypeRegistry):
    from cendry import Field, Model

    class City(Model, collection="cities_structured_test"):
        name: Field[str]

    with pytest.raises(TypeError, match="cannot nest"):
        registry.validate("city", City, "TestModel")


def test_unknown_class_is_invalid(registry: TypeRegistry):
    class RandomClass:
        pass

    with pytest.raises(TypeError):
        registry.validate("val", RandomClass, "TestModel")


# --- Custom registration ---


def test_register_custom_type(registry: TypeRegistry):
    class MyType:
        pass

    registry.register(MyType)
    registry.validate("val", MyType, "TestModel")


def test_register_predicate(registry: TypeRegistry):
    class CustomClass:
        __custom__ = True

    registry.register(lambda cls: hasattr(cls, "__custom__"))
    registry.validate("val", CustomClass, "TestModel")


def test_predicate_raising_typeerror_is_skipped(registry: TypeRegistry):
    """A checker that raises TypeError is silently skipped."""

    def bad_checker(cls: type) -> bool:
        raise TypeError("issubclass() arg 1 must be a class")

    registry.register(bad_checker)
    # Should still reject — the bad checker is skipped, no good checker matches
    with pytest.raises(TypeError, match="unsupported type"):
        registry.validate("val", type("X", (), {}), "TestModel")


def test_predicate_not_matching(registry: TypeRegistry):
    class PlainClass:
        pass

    registry.register(lambda cls: hasattr(cls, "__custom__"))
    with pytest.raises(TypeError):
        registry.validate("val", PlainClass, "TestModel")


# --- default_registry and register_type ---


def test_default_registry_accepts_str():
    from cendry.types import default_registry

    default_registry.validate("name", str, "Test")


def test_register_type_function():
    from cendry.types import default_registry, register_type

    class AnotherType:
        pass

    register_type(AnotherType)
    default_registry.validate("val", AnotherType, "Test")


# --- TypeHandler / BaseTypeHandler ---


def test_base_type_handler_serialize_identity():
    from cendry.types import BaseTypeHandler

    assert BaseTypeHandler().serialize(42) == 42


def test_base_type_handler_deserialize_identity():
    from cendry.types import BaseTypeHandler

    assert BaseTypeHandler().deserialize("hello") == "hello"


def test_base_type_handler_satisfies_protocol():
    from cendry.types import BaseTypeHandler, TypeHandler

    assert isinstance(BaseTypeHandler(), TypeHandler)


# --- register() with handlers ---


def test_register_with_handler(registry: TypeRegistry):
    from cendry.types import BaseTypeHandler

    class Money:
        pass

    registry.register(Money, handler=BaseTypeHandler())
    registry.validate("price", Money, "Test")


def test_register_with_kwargs(registry: TypeRegistry):
    class Money:
        pass

    registry.register(Money, deserialize=lambda v: Money())
    registry.validate("price", Money, "Test")


def test_register_with_serialize_and_deserialize(registry: TypeRegistry):
    class Money:
        pass

    registry.register(Money, serialize=lambda v: {}, deserialize=lambda v: Money())
    registry.validate("price", Money, "Test")


def test_register_serialize_only_raises(registry: TypeRegistry):
    class Money:
        pass

    with pytest.raises(ValueError, match="deserialize"):
        registry.register(Money, serialize=lambda v: v)


def test_register_handler_and_kwargs_exclusive(registry: TypeRegistry):
    from cendry.types import BaseTypeHandler

    class Money:
        pass

    with pytest.raises(ValueError, match="mutually exclusive"):
        registry.register(Money, handler=BaseTypeHandler(), deserialize=lambda v: v)


def test_register_type_only_backwards_compat(registry: TypeRegistry):
    class MyType:
        pass

    registry.register(MyType)
    registry.validate("val", MyType, "Test")


def test_register_predicate_backwards_compat(registry: TypeRegistry):
    class Custom:
        __custom__ = True

    registry.register(lambda cls: hasattr(cls, "__custom__"))
    registry.validate("val", Custom, "Test")


# --- get_handler() ---


def test_get_handler_exact(registry: TypeRegistry):
    from cendry.types import BaseTypeHandler

    class Money:
        pass

    handler = BaseTypeHandler()
    registry.register(Money, handler=handler)
    assert registry.get_handler(Money) is handler


def test_get_handler_predicate(registry: TypeRegistry):
    from cendry.types import BaseTypeHandler

    class Base:
        pass

    class Child(Base):
        pass

    handler = BaseTypeHandler()
    registry.register(lambda cls: issubclass(cls, Base), handler=handler)
    registry.register(Child)
    assert registry.get_handler(Child) is handler


def test_get_handler_none_for_builtin(registry: TypeRegistry):
    assert registry.get_handler(str) is None
    assert registry.get_handler(int) is None


def test_get_handler_none_for_unregistered(registry: TypeRegistry):
    class Unknown:
        pass

    assert registry.get_handler(Unknown) is None


def test_get_handler_kwargs(registry: TypeRegistry):
    class Money:
        pass

    registry.register(Money, deserialize=lambda v: 42)
    handler = registry.get_handler(Money)
    assert handler is not None
    assert handler.deserialize(None) == 42


# --- register_type with handlers ---


def test_register_type_with_kwargs():
    from cendry.types import default_registry, register_type

    class Currency:
        pass

    register_type(Currency, deserialize=lambda v: Currency())
    handler = default_registry.get_handler(Currency)
    assert handler is not None
