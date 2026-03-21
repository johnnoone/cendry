import enum

from pytest_bdd import given, scenario, then, when

from cendry import Field, Model
from cendry import field as cendry_field
from cendry.serialize import deserialize, to_dict

FEATURES = "features"


class Status(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Role(enum.Enum):
    ADMIN = "admin"
    USER = "user"


class UserByValue(Model, collection="bdd_users_val"):
    name: Field[str]
    status: Field[Status]


class UserByName(Model, collection="bdd_users_name"):
    name: Field[str]
    role: Field[Role] = cendry_field(enum_by="name")


@scenario(f"{FEATURES}/enums.feature", "Enum deserializes by value")
def test_enum_by_value():
    pass


@scenario(f"{FEATURES}/enums.feature", "Enum deserializes by name")
def test_enum_by_name():
    pass


@scenario(f"{FEATURES}/enums.feature", "Enum serializes by value")
def test_enum_ser_value():
    pass


@scenario(f"{FEATURES}/enums.feature", "Enum serializes by name")
def test_enum_ser_name():
    pass


@given("a model with enum field stored by value", target_fixture="model_and_data")
def model_by_value():
    return UserByValue, {"name": "Alice", "status": "active"}


@given("a model with enum field stored by name", target_fixture="model_and_data")
def model_by_name():
    return UserByName, {"name": "Alice", "role": "ADMIN"}


@when('I deserialize a document with value "active"', target_fixture="instance")
@when('I deserialize a document with value "ADMIN"', target_fixture="instance")
def do_deserialize(model_and_data):
    cls, data = model_and_data
    return deserialize(cls, "u1", data)


@then("the field is Status.ACTIVE")
def check_status(instance):
    assert instance.status is Status.ACTIVE


@then("the field is Role.ADMIN")
def check_role(instance):
    assert instance.role is Role.ADMIN


@given("a model instance with enum Status.INACTIVE", target_fixture="instance")
def instance_by_value():
    return UserByValue(name="Alice", status=Status.INACTIVE)


@given("a model instance with enum Role.USER stored by name", target_fixture="instance")
def instance_by_name():
    return UserByName(name="Alice", role=Role.USER)


@when("I call to_dict", target_fixture="dict_result")
def call_to_dict(instance):
    return to_dict(instance)


@then('the value is "inactive"')
def check_inactive(dict_result):
    assert dict_result["status"] == "inactive"


@then('the value is "USER"')
def check_user(dict_result):
    assert dict_result["role"] == "USER"
