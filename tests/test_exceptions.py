from cendry import CendryError, DocumentNotFoundError


def test_cendry_error_is_exception():
    assert issubclass(CendryError, Exception)


def test_document_not_found_is_cendry_error():
    assert issubclass(DocumentNotFoundError, CendryError)


def test_document_not_found_message():
    err = DocumentNotFoundError("cities", "SF")
    assert "cities" in str(err)
    assert "SF" in str(err)
