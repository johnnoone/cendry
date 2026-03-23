# Design Decisions

This page explains the reasoning behind Cendry's key design choices.

## Standalone functions over methods on Model

`from_dict()` and `to_dict()` are standalone functions, not classmethods or instance methods.

**Why:** Keeping `Model` lean. Django's `Model.objects` pattern couples queries to the model class, making testing harder and creating import cycles. Cendry's `Model` is just a data container — all behavior lives in the context, query, or serialization modules.

## No Django-style managers

There is no `City.objects.filter(...)` or `City.select(...)`. The context (`Cendry`) is the entry point for all queries.

**Why:** A manager pattern binds models to a global database connection, which is hostile to testing and async. The explicit context makes dependency injection natural.

## Immutable Query objects

`Query.filter()`, `Query.order_by()`, and `Query.limit()` all return new `Query` objects. The original is never mutated.

**Why:** Mutable queries are a source of bugs — saving a reference and then modifying it changes behavior for everyone holding that reference. Immutable queries are safe to share, compose, and cache.

## Copy-pasteable repr

All `__repr__` methods return valid Python:

```python
>>> City.state == "CA"
City.state == 'CA'

>>> City.population.asc()
City.population.asc()

>>> ctx.select(City).filter(City.state == "CA").limit(10)
Query(City, City.state == 'CA', limit=10)
```

**Why:** repr is the primary debugging tool. Copy-pasteable repr means you can take what you see in a debugger, paste it into a REPL, and it works.

## Minimize imports

Prefer methods on existing objects over importing standalone classes:

```python
# Preferred
City.population.asc()
City.state == "CA"

# Also works but more verbose
from cendry import Asc, FieldFilter
Asc(City.population)
FieldFilter("state", "==", "CA")
```

**Why:** Fewer imports means faster onboarding. The descriptor methods are discoverable via autocomplete.

## Field[T] with @dataclass_transform

`Field[T]` is a descriptor that tells type checkers:

- Class access → `FieldDescriptor` (with `.eq()`, `.asc()`, etc.)
- Instance access → `T` (the actual value)

Combined with `@dataclass_transform(kw_only_default=True)` on the metaclass, type checkers understand `__init__`, `dataclasses.fields()`, and `dataclasses.asdict()`.

**Why:** Without this, mypy and ty can't see through the metaclass. The `@dataclass_transform` decorator eliminates most `type: ignore` comments.

## Keyword-only fields

All model fields are `kw_only`. You must write `City(name="SF", state="CA")`, not `City("SF", "CA")`.

**Why:** Positional arguments break when fields are reordered or inherited. Keyword-only is explicit and maintainable.

## Alias resolution

When a field has `alias="displayName"`:

- Filters, ordering, and Firestore I/O use the alias
- `from_dict` / `to_dict` use Python names by default (`by_alias=False`)

**Why:** Python code should use Python names. Firestore-facing operations use Firestore names. The `by_alias` flag gives control when you need it.

## Thin wrapper over Firestore

`FieldFilter` is Firestore's own class, re-exported. Query semantics match Firestore (streaming, collection groups, subcollections). Cendry doesn't invent new query semantics.

**Why:** Users who know Firestore should feel at home. The library adds typing and convenience, not abstraction.

## Backend protocol — abstraction trade-off

Cendry's principle is "thin wrapper over Firestore — don't abstract away Firestore's API." The `Backend` protocol deliberately breaks this rule.

**Why:** Supporting Firestore in Datastore mode enables users to migrate from Datastore to Native mode incrementally. The abstraction is justified because:

- It is **bounded** — the Backend protocol is the only new interface, not a full ORM abstraction layer
- It is **pass-through** — on the Firestore backend, every method is a 2–5 line delegation to the Firestore SDK
- It is **temporary** — once a user migrates to Native mode, the Datastore backend is dropped

## Datastore backend — supported feature subset

The `DatastoreBackend` implements only the features that have a natural equivalent in Datastore. Features without an equivalent raise `CendryError` with a message nudging users to migrate.

| Feature | Supported | Reason |
|---|---|---|
| CRUD (`get`, `save`, `delete`, `update`) | Yes | Direct mapping: Entity get/put/delete |
| Queries (filter, order, limit) | Yes | `query.add_filter()`, `query.order`, `query.fetch(limit=)` |
| AND filters | Yes | Multiple `add_filter()` calls (implicit AND) |
| OR filters | **No** | Datastore has no native OR support |
| Subcollections (`parent=`) | Yes | Maps to ancestor keys |
| Batch writes | Yes | `client.batch()` exists in both SDKs |
| Transactions | Yes | `client.transaction()` exists in both SDKs |
| Collection group queries | **No** | No Datastore equivalent |
| Real-time listeners (`on_snapshot`) | **No** | Datastore has no push-based change notification |
| Async (`AsyncCendry`) | **No** | `google-cloud-datastore` has no `AsyncClient` |
| Transforms (`Increment`, `SERVER_TIMESTAMP`) | **No** | Datastore has no server-side transforms |
| Optimistic locking (`if_unchanged`) | **No** | Datastore has no `LastUpdateOption` equivalent |
| Document metadata (`update_time`, `create_time`) | **No** | Not exposed on Datastore entities |

**Why not emulate unsupported features?** For example, OR queries could be emulated by running multiple queries and merging results. We chose not to because:

- **Semantic parity** — emulated features behave differently under edge cases (ordering, pagination, consistency). Users would discover subtle bugs in production.
- **Performance transparency** — an emulated OR query that fans out to N sub-queries has different cost and latency characteristics. Hiding this violates the "thin wrapper" principle.
- **Migration nudge** — every `CendryError` on an unsupported feature is an explicit signal to migrate. The error message tells the user exactly what to do.

**Why not a read-only subset?** Datastore supports writes (`put`, `delete`, `batch`) natively. Excluding them would force users to maintain two data access layers during migration — defeating the purpose.

**`create()` and `update()` are not atomic** outside transactions on the Datastore backend. Datastore has no "create if not exists" or partial update primitive. Cendry implements these as `get + check + put` (TOCTOU race). This is documented and users are advised to wrap these calls in transactions.

## Type validation at class definition

Invalid `Field[T]` types raise `TypeError` immediately when the class is defined, not when data is queried.

**Why:** Fail fast. A typo in a type annotation should be caught at import time, not in production when a query returns data.
