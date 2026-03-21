from pytest_bdd import given, scenario, then, when

from cendry import Field, Model
from cendry import field as cendry_field
from cendry.serialize import from_dict, to_dict

FEATURES = "features"


class AliasCity(Model, collection="bdd_alias_cities"):
    name: Field[str] = cendry_field(alias="displayName")


@scenario(f"{FEATURES}/aliases.feature", "Field with alias uses alias in filter")
def test_alias_filter():
    pass


@scenario(f"{FEATURES}/aliases.feature", "to_dict uses Python names by default")
def test_to_dict_default():
    pass


@scenario(f"{FEATURES}/aliases.feature", "to_dict uses alias when by_alias is True")
def test_to_dict_alias():
    pass


@scenario(f"{FEATURES}/aliases.feature", "from_dict uses Python names by default")
def test_from_dict_default():
    pass


@scenario(f"{FEATURES}/aliases.feature", "from_dict uses alias when by_alias is True")
def test_from_dict_alias():
    pass


@given('a model with field "name" aliased to "displayName"', target_fixture="model_class")
def model_with_alias():
    return AliasCity


@when('I create a filter with the field equal to "SF"', target_fixture="filter_result")
def create_filter(model_class):
    return model_class.name == "SF"


@then('the filter uses "displayName" as the field name')
def check_filter_alias(filter_result):
    assert filter_result.field_name == "displayName"


@given('a model instance with aliased field "name" set to "SF"', target_fixture="instance")
def model_instance():
    return AliasCity(name="SF")


@when("I call to_dict", target_fixture="dict_result")
def call_to_dict(instance):
    return to_dict(instance)


@when("I call to_dict with by_alias=True", target_fixture="dict_result")
def call_to_dict_alias(instance):
    return to_dict(instance, by_alias=True)


@then('the key is "name"')
def check_key_name(dict_result):
    assert "name" in dict_result


@then('the key is "displayName"')
def check_key_display(dict_result):
    assert "displayName" in dict_result


@given('a dict with key "name" set to "SF"', target_fixture="data")
def dict_python_name():
    return {"name": "SF"}


@given('a dict with key "displayName" set to "SF"', target_fixture="data")
def dict_alias_name():
    return {"displayName": "SF"}


@when("I call from_dict", target_fixture="from_result")
def call_from_dict(data):
    return from_dict(AliasCity, data)


@when("I call from_dict with by_alias=True", target_fixture="from_result")
def call_from_dict_alias(data):
    return from_dict(AliasCity, data, by_alias=True)


@then('the model field "name" is "SF"')
def check_field_value(from_result):
    assert from_result.name == "SF"
