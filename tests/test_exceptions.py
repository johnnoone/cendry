from cendry import CendryError, DocumentNotFound


def test_cendry_error_is_exception():
    assert issubclass(CendryError, Exception)


def test_document_not_found_is_cendry_error():
    assert issubclass(DocumentNotFound, CendryError)


def test_document_not_found_message():
    err = DocumentNotFound("cities", "SF")
    assert "cities" in str(err)
    assert "SF" in str(err)
