# Architecture

## Overview

Cendry is a thin wrapper over `google-cloud-firestore`. It adds typed models, composable filters, and query convenience methods without hiding Firestore's API.

```mermaid
graph TB
    subgraph Your Code
        A[City, Model, collection='cities']
        B["ctx.select(City, City.state == 'CA')"]
        C["ctx.save(city)"]
    end

    subgraph Cendry
        D[model.py<br/>Model, Map, Field]
        E[context.py<br/>Cendry, AsyncCendry]
        F[query.py<br/>Query, AsyncQuery]
        G[serialize.py<br/>from_dict, to_dict]
        H[batch.py<br/>Batch, AsyncBatch]
        I[transaction.py<br/>Txn, AsyncTxn]
        J[metadata.py<br/>get_metadata]
        K[types.py<br/>TypeRegistry, FirestoreValue]
        L[_writes.py<br/>WritesMixin]
        P[backend.py<br/>Backend, AsyncBackend]
        Q[backends/<br/>FirestoreBackend, DatastoreBackend]
    end

    subgraph google-cloud-firestore
        M[Client / AsyncClient]
        N[WriteBatch / Transaction]
        O[DocumentSnapshot]
    end

    A --> D
    B --> E
    C --> E
    E --> F
    E --> G
    E --> H
    E --> I
    H --> L
    I --> L
    L --> G
    E --> P
    P --> Q
    Q --> M
    H --> N
    I --> N
    F --> O
```

## Module dependency graph

```mermaid
graph LR
    context --> query
    context --> serialize
    context --> batch
    context --> transaction
    context --> metadata
    context --> backend
    context --> backends
    batch --> _writes
    transaction --> _writes
    _writes --> serialize
    _writes --> backends
    query --> serialize
    query --> metadata
    serialize --> types
    serialize --> model
    context --> model
    context --> types
    context --> filters
    context --> exceptions
    backends --> backend
```

## Data flow

### Read path

```mermaid
sequenceDiagram
    participant App
    participant Cendry
    participant Serialize
    participant Firestore

    App->>Cendry: ctx.get(City, "SF")
    Cendry->>Firestore: collection("cities").document("SF").get()
    Firestore-->>Cendry: DocumentSnapshot
    Cendry->>Serialize: deserialize(City, doc.id, doc.to_dict())
    Serialize-->>Cendry: City instance
    Cendry->>Cendry: _set_metadata(instance, update_time, create_time)
    Cendry-->>App: City(id="SF", name="San Francisco", ...)
```

### Write path

```mermaid
sequenceDiagram
    participant App
    participant Cendry
    participant Serialize
    participant Firestore

    App->>Cendry: ctx.save(city)
    Cendry->>Serialize: validate_required_fields(city)
    Cendry->>Serialize: to_dict(city, by_alias=True)
    Serialize-->>Cendry: {"name": "SF", "state": "CA", ...}
    Cendry->>Firestore: document.set(data)
    Firestore-->>Cendry: WriteResult(update_time=...)
    Cendry->>Cendry: _set_metadata(city, update_time)
    Cendry-->>App: doc_id
```

### Batch write path

```mermaid
sequenceDiagram
    participant App
    participant Batch
    participant WritesMixin
    participant Firestore

    App->>Batch: with ctx.batch() as batch
    App->>WritesMixin: batch.save(city1)
    WritesMixin->>Firestore: fs_batch.set(doc_ref, data)
    App->>WritesMixin: batch.delete(city2)
    WritesMixin->>Firestore: fs_batch.delete(doc_ref)
    Note over Batch,Firestore: __exit__ triggers commit
    Batch->>Firestore: fs_batch.commit()
```

### Transaction path

```mermaid
sequenceDiagram
    participant App
    participant Cendry
    participant Txn
    participant Firestore

    App->>Cendry: ctx.transaction(transfer_fn)
    Cendry->>Firestore: client.transaction()
    Note over Cendry,Firestore: @transactional handles retry

    loop Attempt (up to max_attempts)
        Cendry->>Txn: transfer_fn(txn)
        Txn->>Firestore: doc.get(transaction=fs_txn)
        Firestore-->>Txn: DocumentSnapshot
        Txn->>Firestore: fs_txn.update(doc_ref, data)
        Txn-->>Cendry: return
        Cendry->>Firestore: commit
    end
```

## Modules

### `model.py`

The core. Contains:

- **`_MapMeta`** — metaclass with `@dataclass_transform`. Rewrites `Field[T]` annotations to plain types, applies `@dataclass(kw_only=True)`, installs `FieldDescriptor` instances, and validates types via `TypeRegistry`.
- **`FieldDescriptor`** — descriptor with dual behavior: filter methods on class access, value access on instances. Tracks `owner` (model class) and `alias` (Firestore name).
- **`FieldFilterResult`** — a filter produced by descriptor methods. Carries owner and alias for repr.
- **`Field[T]`** — marker class with overloaded `__get__` for type checker support.
- **`Map`** / **`Model`** — base classes.

### `context.py`

Entry point for all Firestore operations:

- **`_BaseCendry`** — shared query-building logic, collection ref resolution.
- **`Cendry`** / **`AsyncCendry`** — sync/async contexts with `get`, `find`, `get_many`, `select`, `select_group`, `save`, `create`, `update`, `delete`, `refresh`, `batch`, `save_many`, `delete_many`, `transaction`.
- Populates metadata on every read and write.

### `query.py`

Query builder objects returned by `select()`:

- **`Query[T]`** / **`AsyncQuery[T]`** — immutable, chainable. Hold the underlying Firestore query, model class, filter applicator, and type registry.
- **`Asc`** / **`Desc`** — ordering directives.
- Populates metadata during iteration.

### `serialize.py`

Standalone functions for data conversion:

- **`deserialize`** — Firestore dict → model instance. Always reads by alias.
- **`from_dict`** — user-facing dict → model. `by_alias=False` by default.
- **`to_dict`** — model → dict.
- **`serialize_update_value`** — serialize a value for partial updates, passing sentinels through.
- **`resolve_field_path`** — resolve Python field names to Firestore aliases, recursing into nested Maps.
- **`validate_required_fields`** — raise if required fields are None.
- All accept optional `registry` parameter for custom type handlers.

### `_writes.py`

Shared write logic via `WritesMixin`:

- **`save`**, **`create`**, **`update`**, **`delete`** — used by `Batch`, `AsyncBatch`, `Txn`, `AsyncTxn`.
- Handles overloaded `update`/`delete` signatures (instance or class+ID).

### `batch.py`

- **`Batch`** / **`AsyncBatch`** — context managers wrapping Firestore's `WriteBatch`. Inherit write methods from `WritesMixin`.

### `transaction.py`

- **`Txn`** / **`AsyncTxn`** — context managers wrapping Firestore's `Transaction`. Inherit write methods from `WritesMixin`, add `get`/`find` read methods.

### `metadata.py`

- **`DocumentMetadata`** — dataclass with `update_time` and `create_time`.
- **`get_metadata`** — retrieve metadata for an instance.
- **`_set_metadata`** / **`_clear_metadata`** — internal helpers.
- Storage: `dict[int, (weakref, DocumentMetadata)]` keyed by `id(instance)`.

### `filters.py`

- **`Filter`** — base class with `__and__` / `__or__`.
- **`And`** / **`Or`** — composite filters.
- **`FieldFilter`** — re-exported from Firestore SDK.

### `types.py`

- **`FirestoreValue`** — type alias for values Firestore can natively store (`None | bool | int | float | str | bytes | datetime | GeoPoint | DocumentReference | list | dict`). Referenced in handler docstrings to guide custom type authors.
- **`TypeRegistry`** — validates `Field[T]` annotations at class definition time.
- **`default_registry`** — global singleton with built-in types, built-in handlers (`Decimal` → string, `datetime.date` → datetime at midnight UTC, `datetime.time` → datetime on epoch date), and optional third-party detection (pydantic, attrs, msgspec).

### `backend.py`

- **`Backend`** / **`AsyncBackend`** — protocols defining the contract for pluggable database backends. Every Firestore operation goes through a backend method.

### `backends/`

- **`FirestoreBackend`** / **`FirestoreAsyncBackend`** — default implementations wrapping `google-cloud-firestore`. Each method is a thin delegation (2–5 lines).
- **`DatastoreBackend`** — migration bridge for Firestore in Datastore mode. Supports the common subset and raises clear errors for Native-only features.
- **`DocResult`** / **`WriteResult`** — backend-agnostic result types.
