"""Document metadata tracking."""

import dataclasses
import datetime
import weakref
from typing import Any

from .exceptions import CendryError

# Maps id(instance) -> (weakref_to_instance, DocumentMetadata)
# The weak reference callback removes the entry when the instance is GC'd.
_metadata_store: dict[int, tuple[weakref.ref[Any], "DocumentMetadata"]] = {}


def _make_ref(instance: Any) -> weakref.ref[Any]:
    """Create a weakref with a cleanup callback."""
    obj_id = id(instance)

    def _cleanup(ref: weakref.ref[Any]) -> None:
        _metadata_store.pop(obj_id, None)

    return weakref.ref(instance, _cleanup)


@dataclasses.dataclass
class DocumentMetadata:
    """Firestore document metadata — populated automatically on reads and writes."""

    update_time: datetime.datetime | None = None
    create_time: datetime.datetime | None = None


def get_metadata(instance: Any) -> DocumentMetadata:
    """Get metadata for a model instance.

    Args:
        instance: A Model instance that was read or written through a context.

    Returns:
        The document's metadata.

    Raises:
        CendryError: If the instance has no tracked metadata.
    """
    entry = _metadata_store.get(id(instance))
    if entry is None:
        raise CendryError("No metadata for this instance")
    return entry[1]


def _set_metadata(
    instance: Any,
    *,
    update_time: datetime.datetime | None = None,
    create_time: datetime.datetime | None = None,
) -> None:
    """Set or update metadata for a model instance."""
    obj_id = id(instance)
    entry = _metadata_store.get(obj_id)
    if entry is not None:
        existing = entry[1]
        if update_time is not None:
            existing.update_time = update_time
        if create_time is not None:
            existing.create_time = create_time
    else:
        ref = _make_ref(instance)
        _metadata_store[obj_id] = (ref, DocumentMetadata(update_time=update_time, create_time=create_time))


def _clear_metadata(instance: Any) -> None:
    """Remove metadata for a model instance."""
    _metadata_store.pop(id(instance), None)
