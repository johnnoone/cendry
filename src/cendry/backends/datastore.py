"""Datastore backend implementation."""

import contextlib
import dataclasses
import datetime
from collections.abc import Iterator
from typing import Any, Literal, Self

try:
    from google.cloud import datastore
    from google.cloud.datastore.query import PropertyFilter
except ImportError as exc:  # pragma: no cover
    raise ImportError(  # pragma: no cover
        "google-cloud-datastore is required for DatastoreBackend. "
        "Install it with: pip install cendry[datastore]"
    ) from exc

from ..exceptions import CendryError, DocumentAlreadyExistsError, DocumentNotFoundError
from ..filters import And, Or
from ..model import FieldFilterResult
from .types import DocResult, WriteResult


@dataclasses.dataclass
class _CollectionRef:
    """Internal collection reference for Datastore."""

    kind: str
    ancestor_key: Any | None = None


class _EntitySnapshot:
    """Adapter that makes a Datastore Entity look like a Firestore DocumentSnapshot."""

    def __init__(self, entity: Any) -> None:
        self._entity = entity
        self.id = str(entity.key.id_or_name)
        self.exists = True
        self.update_time = None
        self.create_time = None

    def to_dict(self) -> dict[str, Any]:
        return dict(self._entity)


class _QueryWrapper:
    """Thin wrapper around a Datastore query that accumulates limit/cursor settings."""

    def __init__(self, query: Any) -> None:
        self._query = query
        self._limit: int | None = None
        self._start_cursor: Any | None = None
        self._end_cursor: Any | None = None

    @property
    def query(self) -> Any:
        return self._query

    def add_filter(self, *, filter: Any) -> None:  # noqa: A002
        self._query.add_filter(filter=filter)

    @property
    def order(self) -> list[str]:
        return self._query.order  # type: ignore[no-any-return]

    @order.setter
    def order(self, value: list[str]) -> None:
        self._query.order = value

    @property
    def projection(self) -> list[str]:
        return self._query.projection  # type: ignore[no-any-return]

    @projection.setter
    def projection(self, value: list[str]) -> None:
        self._query.projection = value

    def fetch(self) -> Any:
        kwargs: dict[str, Any] = {}
        if self._limit is not None:
            kwargs["limit"] = self._limit
        if self._start_cursor is not None:
            kwargs["start_cursor"] = self._start_cursor
        if self._end_cursor is not None:
            kwargs["end_cursor"] = self._end_cursor
        return self._query.fetch(**kwargs)

    def stream(self) -> Iterator[_EntitySnapshot]:
        """Iterate results as _EntitySnapshot objects (Firestore-compatible API)."""
        for entity in self.fetch():
            yield _EntitySnapshot(entity)

    def limit(self, n: int) -> "_QueryWrapper":
        """Return a new wrapper with a limit applied."""
        clone = _QueryWrapper(self._query)
        clone._limit = n
        clone._start_cursor = self._start_cursor
        clone._end_cursor = self._end_cursor
        return clone

    def select(self, field_paths: list[str]) -> "_QueryWrapper":
        """Return a new wrapper with projection set."""
        clone = _QueryWrapper(self._query)
        clone._limit = self._limit
        clone._start_cursor = self._start_cursor
        clone._end_cursor = self._end_cursor
        clone.projection = field_paths
        return clone

    def count(self) -> "_CountResult":
        """Return a count aggregation result object."""
        return _CountResult(self)

    def order_by(self, field: str, direction: str = "ASCENDING") -> "_QueryWrapper":
        """Add an ordering and return self for chaining."""
        if direction == "DESCENDING":
            self.order = [*self.order, f"-{field}"]
        else:
            self.order = [*self.order, field]
        return self

    def on_snapshot(self, callback: Any) -> Any:
        """Not supported for Datastore."""
        raise CendryError(
            "Real-time listeners are not supported in Datastore mode. Migrate to Native mode."
        )


class _AggValue:
    """Simple value holder mimicking Firestore's AggregationResult."""

    def __init__(self, value: int) -> None:
        self.value = value


class _CountResult:
    """Adapter that makes Datastore count results match the Firestore count() API."""

    def __init__(self, wrapper: _QueryWrapper) -> None:
        self._wrapper = wrapper

    def get(self) -> list[list[_AggValue]]:
        """Count all entities and return in Firestore-compatible format."""
        total = sum(1 for _ in self._wrapper.fetch())
        return [[_AggValue(total)]]


class _DatastoreWriterAdapter:
    """Adapter that gives a Datastore Batch/Transaction a Firestore-style write API.

    The ``WritesMixin`` calls ``.set()``, ``.create()``, ``.update()``, and
    ``.delete()`` on the writer object.  Datastore batches and transactions use
    ``.put()`` and ``.delete()`` instead, so this thin wrapper translates.
    """

    def __init__(self, ds_writer: Any, client: Any, *, auto_begin: bool = True) -> None:
        self._writer = ds_writer
        self._client = client
        if auto_begin:
            self._writer.begin()

    @property
    def id(self) -> Any:
        """Delegate transaction ID to the underlying writer."""
        return getattr(self._writer, "id", None)

    def set(self, key: Any, data: dict[str, Any]) -> None:
        entity = datastore.Entity(key=key)
        entity.update(data)
        self._writer.put(entity)

    def create(self, key: Any, data: dict[str, Any]) -> None:
        # create semantics (duplicate check) is handled at the backend level,
        # not by the raw writer, so this is identical to set.
        entity = datastore.Entity(key=key)
        entity.update(data)
        self._writer.put(entity)

    def update(self, key: Any, updates: dict[str, Any]) -> None:
        entity = self._client.get(key)
        if entity is None:
            raise DocumentNotFoundError("", str(key.id_or_name))
        entity.update(updates)
        self._writer.put(entity)

    def delete(self, key: Any) -> None:
        self._writer.delete(key)

    # Transaction lifecycle — delegate to the underlying writer
    def begin(self) -> None:
        self._writer.begin()

    def commit(self) -> None:
        self._writer.commit()

    def rollback(self) -> None:
        self._writer.rollback()

    # Context manager support for Batch
    def __enter__(self) -> Self:
        self._writer.__enter__()
        return self

    def __exit__(self, *args: object) -> None:
        self._writer.__exit__(*args)


class DatastoreBackend:
    """Sync Datastore backend wrapping google.cloud.datastore.Client."""

    def __init__(self, *, client: Any = None) -> None:
        if client is None:  # pragma: no cover
            client = datastore.Client()
        self._client = client

    def get_collection_ref(
        self, collection: str, parent_collection: str | None, parent_id: str | None
    ) -> _CollectionRef:
        ancestor_key = None
        if parent_collection is not None and parent_id is not None:
            ancestor_key = self._client.key(parent_collection, parent_id)
        return _CollectionRef(kind=collection, ancestor_key=ancestor_key)

    def get_doc_ref(self, col_ref: _CollectionRef, doc_id: str | None) -> Any:
        if doc_id is None:
            incomplete_key = self._client.key(col_ref.kind, parent=col_ref.ancestor_key)
            keys = self._client.allocate_ids(incomplete_key, 1)
            return keys[0]
        # Datastore distinguishes numeric IDs (int) from named keys (str).
        # Auto-allocated keys use numeric IDs; we store them as strings in Model.id.
        # Convert back to int so lookups match the original key type.
        key_id: int | str = doc_id
        with contextlib.suppress(ValueError):
            key_id = int(doc_id)
        if col_ref.ancestor_key is not None:
            return self._client.key(col_ref.kind, key_id, parent=col_ref.ancestor_key)
        return self._client.key(col_ref.kind, key_id)

    def doc_ref_id(self, doc_ref: Any) -> str:
        return str(doc_ref.id_or_name)

    def get_doc(self, doc_ref: Any, *, transaction: Any | None = None) -> DocResult:
        # Unwrap adapter to get the raw Datastore transaction
        raw_txn = (
            transaction._writer
            if isinstance(transaction, _DatastoreWriterAdapter)
            else transaction
        )
        entity = self._client.get(doc_ref, transaction=raw_txn)
        if entity is None:
            return DocResult(
                exists=False,
                doc_id=str(doc_ref.id_or_name),
                data=None,
                update_time=None,
                create_time=None,
                raw=None,
            )
        return DocResult(
            exists=True,
            doc_id=str(entity.key.id_or_name),
            data=dict(entity),
            update_time=None,
            create_time=None,
            raw=entity,
        )

    def get_all(
        self, doc_refs: list[Any], *, transaction: Any | None = None
    ) -> Iterator[DocResult]:
        raw_txn = (
            transaction._writer
            if isinstance(transaction, _DatastoreWriterAdapter)
            else transaction
        )
        entities = self._client.get_multi(doc_refs, transaction=raw_txn)
        found_keys = {e.key for e in entities if e is not None}
        for ref in doc_refs:
            entity = next((e for e in entities if e is not None and e.key == ref), None)
            if entity is None or ref not in found_keys:
                yield DocResult(
                    exists=False,
                    doc_id=str(ref.id_or_name),
                    data=None,
                    update_time=None,
                    create_time=None,
                    raw=None,
                )
            else:
                yield DocResult(
                    exists=True,
                    doc_id=str(entity.key.id_or_name),
                    data=dict(entity),
                    update_time=None,
                    create_time=None,
                    raw=entity,
                )

    def set_doc(
        self, doc_ref: Any, data: dict[str, Any], *, writer: Any | None = None
    ) -> WriteResult:
        entity = datastore.Entity(key=doc_ref)
        entity.update(data)
        target = writer if writer is not None else self._client
        target.put(entity)
        return WriteResult(update_time=None)

    def create_doc(
        self, doc_ref: Any, data: dict[str, Any], *, writer: Any | None = None
    ) -> WriteResult:
        existing = self._client.get(doc_ref)
        if existing is not None:
            raise DocumentAlreadyExistsError("", str(doc_ref.id_or_name))
        entity = datastore.Entity(key=doc_ref)
        entity.update(data)
        target = writer if writer is not None else self._client
        target.put(entity)
        return WriteResult(update_time=None)

    def update_doc(
        self,
        doc_ref: Any,
        updates: dict[str, Any],
        *,
        writer: Any | None = None,
        precondition: Any | None = None,
    ) -> WriteResult:
        entity = self._client.get(doc_ref)
        if entity is None:
            raise DocumentNotFoundError("", str(doc_ref.id_or_name))
        entity.update(updates)
        target = writer if writer is not None else self._client
        target.put(entity)
        return WriteResult(update_time=None)

    def delete_doc(
        self,
        doc_ref: Any,
        *,
        writer: Any | None = None,
        precondition: Any | None = None,
    ) -> None:
        target = writer if writer is not None else self._client
        target.delete(doc_ref)

    def query(self, col_ref: _CollectionRef) -> _QueryWrapper:
        q = self._client.query(kind=col_ref.kind, ancestor=col_ref.ancestor_key)
        return _QueryWrapper(q)

    def query_group(self, collection: str) -> Any:
        raise CendryError(
            "Collection group queries are not supported in Datastore mode. Migrate to Native mode."
        )

    def apply_filter(self, query: _QueryWrapper, field: str, op: str, value: Any) -> Any:
        # Datastore uses single '=' for equality, not '=='
        ds_op = "=" if op == "==" else op
        query.add_filter(filter=PropertyFilter(field, ds_op, value))
        return query

    def apply_composite(self, query: _QueryWrapper, op: str, filters: list[Any]) -> _QueryWrapper:
        if op == "OR":
            raise CendryError(
                "OR queries are not supported in Datastore mode. Migrate to Native mode."
            )
        resolved = self._extract_filters(filters)
        for f in resolved:
            query.add_filter(filter=f)
        return query

    def _extract_filters(self, filters: list[Any]) -> list[Any]:
        """Recursively extract individual PropertyFilter objects from composite filters."""
        result: list[Any] = []
        for f in filters:
            if isinstance(f, FieldFilterResult):
                result.append(PropertyFilter(f.field_name, f.op, f.value))
            elif isinstance(f, And):
                result.extend(self._extract_filters(list(f.filters)))
            elif isinstance(f, Or):
                raise CendryError(
                    "OR queries are not supported in Datastore mode. Migrate to Native mode."
                )
            else:
                result.append(f)
        return result

    def apply_order(self, query: _QueryWrapper, field: str, direction: str) -> _QueryWrapper:
        if direction == "DESCENDING":
            query.order = [*query.order, f"-{field}"]
        else:
            query.order = [*query.order, field]
        return query

    def apply_limit(self, query: _QueryWrapper, n: int) -> _QueryWrapper:
        query._limit = n
        return query

    def apply_cursor(
        self,
        query: _QueryWrapper,
        cursor_type: Literal["start_at", "start_after", "end_at", "end_before"],
        value: Any,
    ) -> _QueryWrapper:
        cursor_map = {
            "start_at": "_start_cursor",
            "start_after": "_start_cursor",
            "end_at": "_end_cursor",
            "end_before": "_end_cursor",
        }
        setattr(query, cursor_map[cursor_type], value)
        return query

    def stream(self, query: _QueryWrapper) -> Iterator[DocResult]:
        for entity in query.fetch():
            yield DocResult(
                exists=True,
                doc_id=str(entity.key.id_or_name),
                data=dict(entity),
                update_time=None,
                create_time=None,
                raw=entity,
            )

    def select_fields(self, query: _QueryWrapper, fields: list[str]) -> _QueryWrapper:
        query.projection = fields
        return query

    def count(self, query: _QueryWrapper) -> int:
        agg_query = self._client.aggregation_query(query.query).count()
        result = agg_query.fetch()
        for page in result:
            for agg_result in page:
                return agg_result.value  # type: ignore[no-any-return]
        return 0  # pragma: no cover

    def new_batch(self) -> Any:
        return _DatastoreWriterAdapter(self._client.batch(), self._client, auto_begin=True)

    def new_transaction(self, max_attempts: int, read_only: bool) -> Any:
        # Don't auto-begin: Txn.__enter__ calls begin() via the adapter
        return _DatastoreWriterAdapter(self._client.transaction(), self._client, auto_begin=False)

    def commit_batch(self, batch: Any) -> None:
        batch.commit()

    def on_doc_snapshot(self, doc_ref: Any, callback: Any) -> Any:
        raise CendryError(
            "Real-time listeners are not supported in Datastore mode. Migrate to Native mode."
        )

    def on_query_snapshot(self, query: Any, callback: Any) -> Any:
        raise CendryError(
            "Real-time listeners are not supported in Datastore mode. Migrate to Native mode."
        )

    def make_precondition(self, update_time: datetime.datetime) -> Any:
        raise CendryError(
            "Optimistic locking (if_unchanged) is not supported in Datastore mode. "
            "Migrate to Native mode."
        )

    def close(self) -> None:
        pass
