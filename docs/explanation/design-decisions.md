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

## Type validation at class definition

Invalid `Field[T]` types raise `TypeError` immediately when the class is defined, not when data is queried.

**Why:** Fail fast. A typo in a type annotation should be caught at import time, not in production when a query returns data.
