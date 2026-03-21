import dataclasses

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from cendry import Field, Map, Model

FEATURES = "features"


@scenario(f"{FEATURES}/model.feature", "Define a model with a collection")
def test_define_model():
    pass


@scenario(f"{FEATURES}/model.feature", "Model requires a collection")
def test_model_requires_collection():
    pass


@scenario(f"{FEATURES}/model.feature", "Define an embedded map")
def test_define_map():
    pass


@scenario(f"{FEATURES}/model.feature", "Model cannot nest another model")
def test_model_cannot_nest():
    pass


@given(
    parsers.parse('a model class "{name}" with collection "{collection}"'),
    target_fixture="model_class",
)
def model_class(name: str, collection: str):
    return type(name, (Model,), {"__annotations__": {"name": Field[str]}}, collection=collection)


@then(parsers.parse('the model has collection "{collection}"'))
def check_collection(model_class, collection: str):
    assert model_class.__collection__ == collection


@then('the model has an "id" field')
def check_id_field(model_class):
    field_names = {f.name for f in dataclasses.fields(model_class)}
    assert "id" in field_names


@when("I define a model without a collection", target_fixture="model_error")
def define_model_no_collection():
    with pytest.raises(TypeError) as exc_info:

        class Bad(Model):
            name: Field[str]

    return exc_info


@then("a TypeError is raised")
def check_type_error(model_error):
    assert model_error.type is TypeError


@given(
    parsers.parse('a map class "{name}" with fields "{f1}" and "{f2}"'),
    target_fixture="map_class",
)
def map_class_fixture(name: str, f1: str, f2: str):
    return type(name, (Map,), {"__annotations__": {f1: Field[str], f2: Field[int]}})


@then('the map has no "id" field')
def check_no_id(map_class):
    field_names = {f.name for f in dataclasses.fields(map_class)}
    assert "id" not in field_names


@then("the map is a dataclass")
def check_is_dataclass(map_class):
    assert dataclasses.is_dataclass(map_class)


@when(
    parsers.parse('I define a model that nests "{model_name}"'),
    target_fixture="model_error",
)
def define_nested_model(model_class):
    with pytest.raises(TypeError, match="cannot nest") as exc_info:
        type("Bad", (Model,), {"__annotations__": {"ref": Field[model_class]}}, collection="bad")
    return exc_info


@then(parsers.parse('a TypeError is raised with message containing "{text}"'))
def check_error_message(model_error, text: str):
    assert text in str(model_error.value)
