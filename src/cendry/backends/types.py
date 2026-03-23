"""Result types shared by all backends."""

import dataclasses
import datetime
from typing import Any


@dataclasses.dataclass
class DocResult:
    """Result of reading a document from any backend."""

    exists: bool
    doc_id: str
    data: dict[str, Any] | None
    update_time: datetime.datetime | None
    create_time: datetime.datetime | None
    raw: Any  # underlying snapshot/entity, used for cursor pagination


@dataclasses.dataclass
class WriteResult:
    """Result of writing a document to any backend."""

    update_time: datetime.datetime | None
