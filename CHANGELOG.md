# Changelog

## [Unreleased]

### Added

- **Built-in type handlers** — `Decimal`, `datetime.date`, and `datetime.time` now have built-in handlers in the default registry, following NDB conventions (`DateProperty` → datetime at midnight UTC, `TimeProperty` → datetime on 1970-01-01 UTC, `Decimal` → string for lossless round-trip). No manual `register_type()` needed.
- **`FirestoreValue` type alias** — documents the set of types Firestore can natively store; referenced in `TypeHandler` and `BaseTypeHandler` docstrings to guide handler authors
- **Integration tests for all Field[T] types** — 18 tests proving save→get round-trips for every supported type (scalars, containers, enums, maps, custom handlers)

## [0.4.0] — 2026-03-25

### Added

- **Auto-timestamps** — `field(auto_now=True)` and `field(auto_now_add=True)` for automatic `datetime` management on `save()`/`create()`
- **Auto-timestamp validation** — metaclass validates that `auto_now`/`auto_now_add` fields are `datetime` types at class definition time
- **`apply_auto_timestamps`** — standalone function in `serialize.py` for applying timestamp fields

### Fixed

- **`Field[T]` assignment typing** — added `__set__` overload so type checkers no longer reject instance attribute assignment
- **mypy typing errors** — resolved typing issues in backends and context modules

### Documentation

- How-to guide for auto-timestamps
- How-to guide for working with document IDs
- How-to guide for TTL policies
- Expanded Document ID section in models how-to
- Restructured comparison page with Native vs Datastore engine comparison
- Updated `field()` reference with `Args` docstring block

## [0.3.0] — 2026-03-23

### Added

- **Backend protocol** — `Backend` and `AsyncBackend` protocols for pluggable database backends
- **`FirestoreBackend`** / **`FirestoreAsyncBackend`** — explicit Firestore backend classes (extracted from `Cendry`/`AsyncCendry`)
- **`DatastoreBackend`** — support for Firestore in Datastore mode (`pip install cendry[datastore]`), enabling migration from Datastore to Native mode
- **`DocResult`** / **`WriteResult`** — backend-agnostic result types
- **Migration guide** — "How to migrate from Datastore to Native mode" how-to documentation

### Changed

- **`Cendry`** and **`AsyncCendry`** now accept `backend=` parameter (backward compatible — `client=` still works)
- Exception handling (`Conflict` → `DocumentAlreadyExistsError`, `NotFound` → `DocumentNotFoundError`) moved into backend implementations
- All direct Firestore client calls extracted from `context.py` into `FirestoreBackend`

### Known limitations (Datastore backend)

- No async support — `AsyncCendry(backend=DatastoreBackend(...))` raises `CendryError`
- No `OR` queries, collection groups, real-time listeners, optimistic locking, or transforms
- `create()` / `update()` are not atomic outside transactions (TOCTOU race)
- `update_time` / `create_time` metadata not available
- `GeoPoint` and `DocumentReference` type handlers not yet supported

## [0.2.0] — 2026-03-22

### Added

- **Write operations** — `save` (upsert), `create` (insert only), `delete` on `Cendry`/`AsyncCendry`
- **Partial updates** — `update` with field-level changes, dot-notation, Firestore transforms (`Increment`, `ArrayUnion`, `DELETE_FIELD`, `SERVER_TIMESTAMP`)
- **Refresh** — `refresh(instance)` re-fetches from Firestore and mutates in-place
- **Batch writes** — `save_many`, `delete_many` (max 500, atomic), `batch()` context manager with `Batch`/`AsyncBatch`
- **Transactions** — `transaction(fn)` callback with auto-retry, `transaction()` context manager (single attempt), `Txn`/`AsyncTxn` with read + write methods
- **`DocumentAlreadyExistsError`** — raised by `create` when document exists, preserves `__cause__`
- **Firestore re-exports** — `DELETE_FIELD`, `SERVER_TIMESTAMP`, `Increment`, `ArrayUnion`, `ArrayRemove`, `Maximum`, `Minimum`
- **`validate_required_fields`** — standalone function in `serialize.py`
- **Optimistic locking** — `get_metadata(instance)` returns `DocumentMetadata` with `update_time`/`create_time`, tracked via weakref; `if_unchanged=True` on `update`/`delete` passes Firestore `LastUpdateOption` precondition
- **`DocumentMetadata`** and **`get_metadata`** — document metadata tracking, auto-populated on reads and writes

### Changed

- **`type_registry` threading** — custom `TypeRegistry` on context now flows through all serialization, deserialization, query, and write paths
- **`to_dict`/`from_dict`/`deserialize`** — accept optional `registry` parameter
- **`Query`/`AsyncQuery`** — accept and propagate `registry` through all construction sites
- **`resolve_field_path`** — recurses into nested Map fields for dot-notation alias resolution
- **`serialize_update_value`** — accepts `hint` parameter for proper container serialization (e.g. `list[Money]`)
- **`_cursor_value`** — uses `to_dict` instead of `dataclasses.asdict` for proper type handler support
- **`WritesMixin`** — shared write methods extracted to `_writes.py`, used by `Batch`, `AsyncBatch`, `Txn`, `AsyncTxn`
- **`assert` → `CendryError`** — defensive guards safe under `-O` flag
- **`resolve_field_path` / `validate_required_fields`** — cached for O(1) lookups
- **`BATCH_LIMIT`** — extracted as named constant with `_check_batch_limit` helper
- **Migrated docs** from mkdocs-material to [Zensical](https://zensical.org/)

### Documentation

- **Firestore intro** — "What is Firestore?" explanation with links to official docs
- **SDK vs NDB vs Cendry** — 10 side-by-side use cases comparing all three approaches
- **Async tutorial** — full `async`/`await` tutorial with sync-vs-async comparison table
- **Mermaid architecture diagrams** — module graph, dependency graph, read/write/batch/transaction sequence diagrams
- **How-To guides** — split into single-doc operations + batch/transactions
- **Integration testing guide** — testcontainers setup, fixtures, CI configuration
- **Fire color palette** — custom CSS theme for docs

### Testing

- **523 unit tests** — 100% coverage on 1195 source lines
- **38 integration tests** — against real Firestore emulator via testcontainers
- **12 BDD integration scenarios** — CRUD, batch, and transaction feature files

## [0.1.0] — 2026-03-21

First release — read-only Firestore ODM for Python >= 3.13.

### Added

- **Models** — `Model`, `Map`, `Field[T]`, `field()` with `dataclass_transform` for full IDE support
- **Queries** — `Cendry` (sync) and `AsyncCendry` (async) contexts with `get`, `find`, `get_many`, `select`, `select_group`
- **Query object** — chainable `Query`/`AsyncQuery` with `filter`, `order_by`, `limit`, `first`, `one`, `exists`, `count`, `to_list`, `paginate`
- **Filters** — Python operators (`==`, `!=`, `>`, `<`, `&`, `|`), named methods, `FieldFilter` re-export, `And`/`Or` composition
- **Field aliases** — `field(alias="firestoreName")` for when Python and Firestore names differ
- **Enum support** — `Field[MyEnum]` with `field(enum_by="value"|"name")` auto-conversion
- **Type validation** — `TypeRegistry` validates `Field[T]` at class definition time
- **Type handlers** — `register_type(MyType, handler=..., serialize=..., deserialize=...)` for custom type conversion
- **Serialization** — `from_dict`, `to_dict` standalone functions with alias support
- **Context manager** — `with Cendry() as ctx:` / `async with AsyncCendry() as ctx:`
- **Copy-pasteable repr** — all filters, queries, and ordering objects produce valid Python repr
- **Subcollections** — `parent=` parameter for nested document queries
- **Collection groups** — `select_group` for cross-subcollection queries
