from pytest_bdd import given, scenario, then, when

from cendry import Field, Model
from cendry.serialize import deserialize
from cendry.types import BaseTypeHandler, TypeRegistry, default_registry

FEATURES = "features"


class Token:
    def __init__(self, value: str) -> None:
        self.value = value


class TokenHandler(BaseTypeHandler):
    def serialize(self, value: Token) -> str:
        return value.value

    def deserialize(self, value: str) -> Token:
        return Token(value=value)


default_registry.register(Token, handler=TokenHandler())


class Wallet(Model, collection="bdd_wallets"):
    name: Field[str]
    token: Field[Token]


class MultiWallet(Model, collection="bdd_multi_wallets"):
    name: Field[str]
    tokens: Field[list[Token]]


@scenario(f"{FEATURES}/type_handlers.feature", "Register type with handler class")
def test_handler_class():
    pass


@scenario(f"{FEATURES}/type_handlers.feature", "Register type with kwargs")
def test_handler_kwargs():
    pass


@scenario(f"{FEATURES}/type_handlers.feature", "Serialize without deserialize raises")
def test_serialize_only():
    pass


@scenario(f"{FEATURES}/type_handlers.feature", "Handler and kwargs are mutually exclusive")
def test_exclusive():
    pass


@scenario(f"{FEATURES}/type_handlers.feature", "Container of handled type")
def test_container():
    pass


@given("a custom type with a handler", target_fixture="custom_type")
def custom_with_handler():
    return Token


@when("I define a model with that type", target_fixture="model_result")
def define_model(custom_type):
    return ("success", Wallet)


@then("the model is created successfully")
def check_model(model_result):
    assert model_result[0] == "success"


@given("a custom type registered with deserialize kwarg", target_fixture="kwarg_registry")
def custom_with_kwargs():
    registry = TypeRegistry()

    class Coin:
        def __init__(self, v: str) -> None:
            self.v = v

    registry.register(Coin, deserialize=lambda v: Coin(v))
    return registry, Coin


@when("I deserialize a document with that type", target_fixture="deser_result")
def deserialize_kwarg(kwarg_registry):
    registry, coin_cls = kwarg_registry
    handler = registry.get_handler(coin_cls)
    assert handler is not None
    return handler.deserialize("gold")


@then("the value is converted by the handler")
def check_converted(deser_result):
    assert deser_result.v == "gold"


@when("I register a type with serialize but no deserialize", target_fixture="error_result")
def register_serialize_only():
    registry = TypeRegistry()
    try:
        registry.register(str, serialize=lambda v: v)
        return None
    except ValueError as e:
        return e


@then("ValueError is raised")
def check_value_error(error_result):
    assert isinstance(error_result, ValueError)


@when("I register a type with both handler and kwargs", target_fixture="error_result")
def register_both():
    registry = TypeRegistry()
    try:
        registry.register(str, handler=BaseTypeHandler(), deserialize=lambda v: v)
        return None
    except ValueError as e:
        return e


@given("a custom type registered with a handler", target_fixture="container_info")
def custom_for_container():
    return Token, MultiWallet


@when("I deserialize a list of that type", target_fixture="container_result")
def deserialize_list(container_info):
    _, model_cls = container_info
    return deserialize(model_cls, "w1", {"name": "My Wallet", "tokens": ["abc", "def"]})


@then("each element is converted by the handler")
def check_each_element(container_result):
    assert len(container_result.tokens) == 2
    assert all(isinstance(t, Token) for t in container_result.tokens)
    assert container_result.tokens[0].value == "abc"
