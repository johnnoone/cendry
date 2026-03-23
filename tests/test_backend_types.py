import datetime

from cendry.backend import AsyncBackend, Backend
from cendry.backends.types import DocResult, WriteResult


def test_doc_result_fields():
    doc = DocResult(
        exists=True,
        doc_id="SF",
        data={"name": "San Francisco"},
        update_time=datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC),
        create_time=datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC),
        raw=None,
    )
    assert doc.exists is True
    assert doc.doc_id == "SF"
    assert doc.data == {"name": "San Francisco"}


def test_doc_result_not_exists():
    doc = DocResult(
        exists=False, doc_id="NOPE", data=None, update_time=None, create_time=None, raw=None
    )
    assert doc.exists is False
    assert doc.data is None


def test_write_result():
    wr = WriteResult(update_time=datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC))
    assert wr.update_time is not None


def test_write_result_none():
    wr = WriteResult(update_time=None)
    assert wr.update_time is None


def test_backend_is_protocol():
    assert Backend is not None
    assert AsyncBackend is not None
