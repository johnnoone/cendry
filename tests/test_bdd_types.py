import dataclasses
import datetime
from decimal import Decimal
from typing import Any, TypedDict

from pytest_bdd import given, parsers, scenario, then, when

from cendry import Field, Map, Model
from cendry.types import default_registry
from google.cloud.firestore_v1._helpers import GeoPoint
from google.cloud.firestore_v1.document import DocumentReference

FEATURES = "features"

_counter = 0


def _unique_name() -> str:
    global _counter  # noqa: PLW0603
    _counter += 1
    return f"bdd_types_{_counter}"


# --- Type resolution ---

_TYPE_MAP: dict[str, Any] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "bytes": bytes,
    "Decimal": Decimal,
    "datetime": datetime.datetime,
    "GeoPoint": GeoPoint,
    "DocumentReference": DocumentReference,
    "complex": complex,
}


def _split_type_args(s: str) -> list[str]:
    """Split type args respecting nested brackets."""
    args: list[str] = []
    depth = 0
    current = ""
    for ch in s:
        if ch == "[":
            depth += 1
            current += ch
        elif ch == "]":
            depth -= 1
            current += ch
        elif ch == "," and depth == 0:
            args.append(current)
            current = ""
        else:
            current += ch
    if current:
        args.append(current)
    return args


def _resolve_type(type_str: str) -> Any:
    """Resolve a type string from feature files to an actual Python type."""
    if type_str in _TYPE_MAP:
        return _TYPE_MAP[type_str]

    # Optional: "str | None"
    if type_str.endswith(" | None"):
        return _resolve_type(type_str[:-7]) | None

    # Container: "list[str]", "dict[str, int]", etc.
    if "[" in type_str:
        container_name, rest = type_str.split("[", 1)
        rest = rest.rstrip("]")
        container = {"list": list, "set": set, "tuple": tuple, "dict": dict}[container_name]
        args = _split_type_args(rest)
        resolved = tuple(_resolve_type(a.strip()) for a in args)
        return container[resolved] if len(resolved) > 1 else container[resolved[0]]

    if type_str == "Map":
        ns = {"__annotations__": {"name": Field[str]}}
        return type(f"TestMap_{_unique_name()}", (Map,), ns)

    if type_str == "dataclass":

        @dataclasses.dataclass
        class TestDC:
            x: float

        return TestDC

    if type_str == "TypedDict":

        class TestTD(TypedDict):
            key: str

        return TestTD

    if type_str == "Model":
        ns = {"__annotations__": {"name": Field[str]}}
        return type(f"TestModel_{_unique_name()}", (Model,), ns, collection=_unique_name())

    if type_str == "UnknownClass":
        return type("UnknownClass", (), {})

    msg = f"Unknown type string: {type_str}"
    raise ValueError(msg)


# --- Scenarios ---


@scenario(f"{FEATURES}/types.feature", "Valid scalar types are accepted")
def test_valid_scalars():
    pass


@scenario(f"{FEATURES}/types.feature", "Firestore SDK types are accepted")
def test_sdk_types():
    pass


@scenario(f"{FEATURES}/types.feature", "Invalid scalar type is rejected")
def test_invalid_scalar():
    pass


@scenario(f"{FEATURES}/types.feature", "Optional valid type is accepted")
def test_optional_valid():
    pass


@scenario(f"{FEATURES}/types.feature", "Optional invalid type is rejected")
def test_optional_invalid():
    pass


@scenario(f"{FEATURES}/types.feature", "List of valid type is accepted")
def test_list_valid():
    pass


@scenario(f"{FEATURES}/types.feature", "List of invalid type is rejected")
def test_list_invalid():
    pass


@scenario(f"{FEATURES}/types.feature", "Dict with string keys is accepted")
def test_dict_valid():
    pass


@scenario(f"{FEATURES}/types.feature", "Dict with non-string keys is rejected")
def test_dict_invalid():
    pass


@scenario(f"{FEATURES}/types.feature", "Set of valid type is accepted")
def test_set_valid():
    pass


@scenario(f"{FEATURES}/types.feature", "Tuple of valid types is accepted")
def test_tuple_valid():
    pass


@scenario(f"{FEATURES}/types.feature", "Nested container with valid types is accepted")
def test_nested_valid():
    pass


@scenario(f"{FEATURES}/types.feature", "Nested container with invalid inner type is rejected")
def test_nested_invalid():
    pass


@scenario(f"{FEATURES}/types.feature", "Map subclass is accepted")
def test_map():
    pass


@scenario(f"{FEATURES}/types.feature", "Dataclass is accepted")
def test_dataclass():
    pass


@scenario(f"{FEATURES}/types.feature", "TypedDict is accepted")
def test_typeddict():
    pass


@scenario(f"{FEATURES}/types.feature", "Model nested in Model is rejected")
def test_model_nested():
    pass


@scenario(f"{FEATURES}/types.feature", "Unknown class is rejected")
def test_unknown():
    pass


@scenario(f"{FEATURES}/types.feature", "User-registered type is accepted")
def test_registered_type():
    pass


@scenario(f"{FEATURES}/types.feature", "User-registered predicate accepts matching types")
def test_registered_predicate():
    pass


# --- Steps ---


@when(
    parsers.parse('I define a model with a field of type "{type_str}"'),
    target_fixture="model_result",
)
def define_model_with_type(type_str):
    resolved = _resolve_type(type_str)
    try:
        name = f"DynModel_{_unique_name()}"
        cls = type(
            name,
            (Model,),
            {"__annotations__": {"val": Field[resolved]}},
            collection=_unique_name(),
        )
        return ("success", cls)
    except TypeError as e:
        return ("error", e)


@then("the model is created successfully")
def model_created(model_result):
    status, value = model_result
    assert status == "success", f"Expected success, got error: {value}"


@then("a TypeError is raised")
def type_error_raised(model_result):
    status, _ = model_result
    assert status == "error"


@then(parsers.parse('a TypeError is raised with message containing "{text}"'))
def type_error_with_message(model_result, text):
    status, error = model_result
    assert status == "error", f"Expected error, got success"
    assert text in str(error), f"Expected '{text}' in '{error}'"


@given("a custom class registered in the type registry")
def register_custom_type():
    cls = type("RegisteredCustom", (), {})
    default_registry.register(cls)
    _TYPE_MAP["RegisteredCustom"] = cls


@given(parsers.parse('a predicate that accepts classes with "{attr}" attribute'))
def register_predicate(attr):
    default_registry.register(lambda cls: hasattr(cls, attr))
    custom_cls = type("CustomClass", (), {attr: True})
    _TYPE_MAP["CustomClass"] = custom_cls
