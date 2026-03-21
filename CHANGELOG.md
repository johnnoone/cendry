# Changelog

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
