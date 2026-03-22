from unittest.mock import MagicMock

from pytest_bdd import given, parsers, scenario, then, when

from cendry import Cendry, CendryError
from tests.conftest import SF_DATA, City

FEATURES = "features"


@scenario(f"{FEATURES}/batch.feature", "Save many documents atomically")
def test_save_many():
    pass


@scenario(f"{FEATURES}/batch.feature", "Save many over 500 raises error")
def test_save_many_over_500():
    pass


@scenario(f"{FEATURES}/batch.feature", "Delete many documents by instances")
def test_delete_many():
    pass


@scenario(f"{FEATURES}/batch.feature", "Batch context manager commits on exit")
def test_batch_commits():
    pass


@scenario(f"{FEATURES}/batch.feature", "Batch context manager does not commit on exception")
def test_batch_no_commit_on_error():
    pass


@given(
    parsers.parse("{count:d} City instances with ids"),
    target_fixture="ctx_and_instances",
)
def n_cities(count: int):
    client = MagicMock()
    instances = [City(**SF_DATA, id=f"city-{i}") for i in range(count)]
    return Cendry(client=client), instances, client


@given("a batch context manager", target_fixture="ctx_and_instances")
def batch_ctx():
    client = MagicMock()
    return Cendry(client=client), [], client


@when("I save them all with save_many", target_fixture="result")
def save_many(ctx_and_instances):
    ctx, instances, _ = ctx_and_instances
    try:
        ctx.save_many(instances)
        return None
    except CendryError as e:
        return e


@when("I delete them all with delete_many", target_fixture="result")
def delete_many(ctx_and_instances):
    ctx, instances, _ = ctx_and_instances
    ctx.delete_many(instances)
    return


@when("I save a City inside the batch", target_fixture="result")
def save_in_batch(ctx_and_instances):
    ctx, _, _ = ctx_and_instances
    with ctx.batch() as batch:
        batch.save(City(**SF_DATA, id="SF"))
    return


@when("an exception occurs inside the batch", target_fixture="result")
def exception_in_batch(ctx_and_instances):
    ctx, _, _ = ctx_and_instances
    try:
        with ctx.batch():
            raise ValueError("boom")
    except ValueError:
        pass
    return


@then(parsers.parse("all {count:d} documents are written to Firestore"))
def check_set_count(ctx_and_instances, count: int):
    _, _, client = ctx_and_instances
    assert client.batch.return_value.set.call_count == count


@then(parsers.parse("all {count:d} documents are deleted from Firestore"))
def check_delete_count(ctx_and_instances, count: int):
    _, _, client = ctx_and_instances
    assert client.batch.return_value.delete.call_count == count


@then(parsers.parse('a CendryError is raised with message "{message}"'))
def check_cendry_error(result, message: str):
    assert isinstance(result, CendryError)
    assert message in str(result)


@then("the batch commits on exit")
def check_batch_committed(ctx_and_instances):
    _, _, client = ctx_and_instances
    client.batch.return_value.commit.assert_called_once()


@then("the batch does not commit")
def check_batch_not_committed(ctx_and_instances):
    _, _, client = ctx_and_instances
    client.batch.return_value.commit.assert_not_called()
