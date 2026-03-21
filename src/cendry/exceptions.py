class CendryError(Exception):
    """Base exception for all Cendry errors."""


class DocumentNotFoundError(CendryError):
    """Raised when a document does not exist."""

    def __init__(self, collection: str, document_id: str) -> None:
        self.collection = collection
        self.document_id = document_id
        super().__init__(f"Document '{document_id}' not found in collection '{collection}'")
