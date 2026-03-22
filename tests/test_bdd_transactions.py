from unittest.mock import MagicMock

from pytest_bdd import given, scenario, then, when

from cendry import DocumentNotFoundError
from cendry.transaction import Txn
from cendry.types import default_registry
from tests.conftest import SF_DATA, City, make_mock_document

FEATURES = "features"


@scenario(f"{FEATURES}/transactions.feature", "Transaction context manager reads and writes")
def test_txn_read_write():
    pass


@scenario(
    f"{FEATURES}/transactions.feature",
    "Transaction context manager rolls back on exception",
)
def test_txn_rollback():
    pass


@scenario(f"{FEATURES}/transactions.feature", "Transaction get on missing document raises error")
def test_txn_get_missing():
    pass


@scenario(f"{FEATURES}/transactions.feature", "Transaction find on missing document returns None")
def test_txn_find_missing():
    pass


def _make_txn_ctx():
    client = MagicMock()
    fs_txn = MagicMock()

    def get_collection_ref(model_class, parent=None):
        return client.collection(model_class.__collection__)

    txn = Txn(fs_txn, get_collection_ref, default_registry)
    return txn, fs_txn, client


@given('a City document "SF" in Firestore', target_fixture="txn_ctx")
def city_in_firestore():
    txn, fs_txn, client = _make_txn_ctx()
    doc = make_mock_document("SF", SF_DATA)
    doc.update_time = None
    doc.create_time = None
    client.collection.return_value.document.return_value.get.return_value = doc
    return txn, fs_txn, client


@given("an empty Firestore collection", target_fixture="txn_ctx")
def empty_collection():
    txn, fs_txn, client = _make_txn_ctx()
    doc = make_mock_document("NOPE", {}, exists=False)
    client.collection.return_value.document.return_value.get.return_value = doc
    return txn, fs_txn, client


@when("I read and update it in a transaction context manager", target_fixture="result")
def read_and_update(txn_ctx):
    txn, _fs_txn, _ = txn_ctx
    with txn:
        city = txn.get(City, "SF")
        txn.update(city, {"population": 900_000})
    return city


@when("an exception occurs inside the transaction", target_fixture="result")
def exception_in_txn(txn_ctx):
    txn, _, _ = txn_ctx
    try:
        with txn:
            raise ValueError("boom")
    except ValueError:
        pass
    return


@when("I get a missing document in a transaction", target_fixture="result")
def get_missing(txn_ctx):
    txn, _, _ = txn_ctx
    try:
        with txn:
            return txn.get(City, "NOPE")
    except DocumentNotFoundError as e:
        return e


@when("I find a missing document in a transaction", target_fixture="result")
def find_missing(txn_ctx):
    txn, _, _ = txn_ctx
    with txn:
        return txn.find(City, "NOPE")


@then("the read returns the document")
def check_read(result):
    assert isinstance(result, City)
    assert result.name == "San Francisco"


@then("the update is queued")
def check_update_queued(txn_ctx):
    _, fs_txn, _ = txn_ctx
    fs_txn.update.assert_called_once()


@then("the transaction rolls back")
def check_rollback(txn_ctx):
    _, fs_txn, _ = txn_ctx
    fs_txn._rollback.assert_called_once()
    fs_txn._commit.assert_not_called()


@then("a DocumentNotFoundError is raised")
def check_not_found(result):
    assert isinstance(result, DocumentNotFoundError)


@then("the result is None")
def check_none(result):
    assert result is None
