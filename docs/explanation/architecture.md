# Architecture

## Overview

Cendry is a thin wrapper over `google-cloud-firestore`. It adds typed models, composable filters, and query convenience methods without hiding Firestore's API.

```
┌─────────────────────────────────────┐
│  Your Code                          │
│  City(Model, collection="cities")   │
│  ctx.select(City, City.state=="CA") │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  Cendry                             │
│  ┌──────────┐  ┌─────────────────┐  │
│  │ model.py │  │ query.py        │  │
│  │ Field[T] │  │ Query/AsyncQuery│  │
│  │ Map      │  │ Asc/Desc        │  │
│  │ Model    │  └─────────────────┘  │
│  └──────────┘  ┌─────────────────┐  │
│  ┌──────────┐  │ serialize.py    │  │
│  │context.py│  │ from_dict       │  │
│  │ Cendry   │  │ to_dict         │  │
│  │AsyncCndry│  │ deserialize     │  │
│  └──────────┘  └─────────────────┘  │
│  ┌──────────┐  ┌─────────────────┐  │
│  │filters.py│  │ types.py        │  │
│  │ And, Or  │  │ TypeRegistry    │  │
│  │ Filter   │  │ register_type   │  │
│  └──────────┘  └─────────────────┘  │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  google-cloud-firestore             │
│  Client / AsyncClient               │
│  FieldFilter, DocumentSnapshot      │
└─────────────────────────────────────┘
```

## Modules

### `model.py`

The core. Contains:

- **`_MapMeta`** — metaclass with `@dataclass_transform`. Rewrites `Field[T]` annotations to plain types, applies `@dataclass(kw_only=True)`, installs `FieldDescriptor` instances, and validates types via `TypeRegistry`.
- **`FieldDescriptor`** — descriptor with dual behavior: filter methods on class access, value access on instances. Tracks `owner` (model class) and `alias` (Firestore name).
- **`FieldFilterResult`** — a filter produced by descriptor methods. Carries owner and alias for repr.
- **`Field[T]`** — marker class with overloaded `__get__` for type checker support.
- **`Map`** / **`Model`** — base classes.

### `query.py`

Query builder objects returned by `select()`:

- **`Query[T]`** / **`AsyncQuery[T]`** — immutable, chainable. Hold the underlying Firestore query, model class, and filter applicator. Track filters, ordering, and limit for repr.
- **`Asc`** / **`Desc`** — ordering directives.

### `context.py`

Entry point for all Firestore operations:

- **`_BaseCendry`** — shared query-building logic.
- **`Cendry`** / **`AsyncCendry`** — sync/async contexts with `get`, `find`, `get_many`, `select`, `select_group`.

### `serialize.py`

Standalone functions for data conversion:

- **`deserialize`** — Firestore dict → model instance. Always reads by alias. Uses cached `get_type_hints`.
- **`from_dict`** — user-facing dict → model. `by_alias=False` by default.
- **`to_dict`** — model → dict.

### `filters.py`

- **`Filter`** — base class with `__and__` / `__or__`.
- **`And`** / **`Or`** — composite filters.
- **`FieldFilter`** — re-exported from Firestore SDK.

### `types.py`

- **`TypeRegistry`** — validates `Field[T]` annotations at class definition time.
- **`default_registry`** — global singleton with built-in types + optional third-party detection.
