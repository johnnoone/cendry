from cendry import CendryError, DocumentAlreadyExistsError, DocumentNotFoundError


def test_cendry_error_is_exception():
    assert issubclass(CendryError, Exception)


def test_document_not_found_is_cendry_error():
    assert issubclass(DocumentNotFoundError, CendryError)


def test_document_not_found_message():
    err = DocumentNotFoundError("cities", "SF")
    assert "cities" in str(err)
    assert "SF" in str(err)


def test_document_already_exists_error():
    error = DocumentAlreadyExistsError("cities", "SF")
    assert isinstance(error, CendryError)
    assert error.collection == "cities"
    assert error.document_id == "SF"
    assert "SF" in str(error)
    assert "cities" in str(error)
