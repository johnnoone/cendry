# Firestore SDK vs NDB vs Cendry

Side-by-side comparison of common use cases across three approaches:

- **Firestore SDK** — `google-cloud-firestore`, the official low-level client
- **NDB** — `google-cloud-ndb`, the legacy App Engine ORM (Datastore mode only)
- **Cendry** — typed ODM for Firestore Native mode

!!! warning "NDB is deprecated for new projects"
    [Cloud NDB](https://github.com/googleapis/python-ndb) only works with **Firestore in Datastore mode** — it does [not support Firestore Native mode](https://github.com/googleapis/python-ndb/issues/140). Google recommends [Firestore Native mode for all new applications](https://cloud.google.com/datastore/docs/firestore-or-datastore). NDB is shown here for developers migrating from App Engine.

---

## Define a model

=== "NDB (deprecated)"

    ```python
    from google.cloud import ndb

    class City(ndb.Model):
        name = ndb.StringProperty()
        state = ndb.StringProperty()
        population = ndb.IntegerProperty()
        mayor = ndb.StructuredProperty(Mayor)  # nested
    ```

    No type annotations, no IDE autocomplete on fields.

=== "Firestore SDK"

    No model layer — you work with raw dicts.

    ```python
    # No model definition — just use dicts everywhere
    city_data = {
        "name": "San Francisco",
        "state": "CA",
        "population": 870000,
    }
    ```

=== "Cendry"

    ```python
    from cendry import Model, Map, Field, field

    class Mayor(Map):
        name: Field[str]
        since: Field[int]

    class City(Model, collection="cities"):
        name: Field[str]
        state: Field[str]
        population: Field[int]
        mayor: Field[Mayor | None] = field(default=None)
    ```

    Type annotations validated at class definition. Full IDE support.

---

## Read a document

=== "NDB (deprecated)"

    ```python
    city = City.get_by_id("SF")
    if city is None:
        raise Exception("Not found")
    print(city.name)
    ```

=== "Firestore SDK"

    ```python
    from google.cloud.firestore import Client

    client = Client()
    doc = client.collection("cities").document("SF").get()
    if not doc.exists:
        raise Exception("Not found")
    data = doc.to_dict()
    name = data["name"]       # no type safety
    population = data["pop"]  # typo? no error at all
    ```

=== "Cendry"

    ```python
    from cendry import Cendry

    with Cendry() as ctx:
        city = ctx.get(City, "SF")  # raises DocumentNotFoundError
        print(city.name)            # typed, IDE autocomplete
        print(city.population)      # typo → immediate error
    ```

---

## Query with filters

=== "NDB (deprecated)"

    ```python
    cities = City.query(
        City.state == "CA",
        City.population > 1_000_000,
    ).order(-City.population).fetch(10)
    ```

=== "Firestore SDK"

    ```python
    from google.cloud.firestore_v1.base_query import FieldFilter

    query = (
        client.collection("cities")
        .where(filter=FieldFilter("state", "==", "CA"))
        .where(filter=FieldFilter("population", ">", 1_000_000))
        .order_by("population", direction="DESCENDING")
        .limit(10)
    )
    for doc in query.stream():
        data = doc.to_dict()
        print(data["name"], data["population"])
    ```

=== "Cendry"

    ```python
    cities = (
        ctx.select(City)
        .filter(City.state == "CA", City.population > 1_000_000)
        .order_by(City.population.desc())
        .limit(10)
        .to_list()
    )
    for city in cities:
        print(city.name, city.population)
    ```

---

## Save a document

=== "NDB (deprecated)"

    ```python
    city = City(name="San Francisco", state="CA", population=870000)
    city.put()
    print(city.key.id())
    ```

=== "Firestore SDK"

    ```python
    client.collection("cities").document("SF").set({
        "name": "San Francisco",
        "state": "CA",
        "population": 870000,
    })
    ```

=== "Cendry"

    ```python
    city = City(name="San Francisco", state="CA", population=870_000)
    ctx.save(city)  # auto-generates ID, validates fields
    print(city.id)  # ID set automatically
    ```

---

## Partial update

=== "NDB (deprecated)"

    ```python
    city = City.get_by_id("SF")
    city.population = 900_000
    city.put()  # overwrites entire entity — no partial update
    ```

    NDB doesn't support partial updates — you must fetch, modify, and re-save the entire entity.

=== "Firestore SDK"

    ```python
    from google.cloud.firestore import Increment

    client.collection("cities").document("SF").update({
        "population": Increment(1000),
        "mayor.name": "Jane",
    })
    ```

=== "Cendry"

    ```python
    from cendry import Increment

    ctx.update(city, {
        "population": Increment(1000),
        "mayor.name": "Jane",
    })
    # or by class + ID:
    ctx.update(City, "SF", {"population": Increment(1000)})
    ```

---

## Delete a document

=== "NDB (deprecated)"

    ```python
    key = ndb.Key("City", "SF")
    key.delete()
    ```

=== "Firestore SDK"

    ```python
    client.collection("cities").document("SF").delete()
    # silent if it doesn't exist — no way to know
    ```

=== "Cendry"

    ```python
    ctx.delete(city)
    ctx.delete(City, "SF")
    ctx.delete(City, "SF", must_exist=True)  # raises if missing
    ```

---

## Batch writes

=== "NDB (deprecated)"

    ```python
    ndb.put_multi([city1, city2, city3])
    ndb.delete_multi([key1, key2])
    ```

=== "Firestore SDK"

    ```python
    batch = client.batch()
    for city_data in cities_data:
        ref = client.collection("cities").document()
        batch.set(ref, city_data)
    batch.commit()
    ```

=== "Cendry"

    ```python
    ctx.save_many(cities)  # one line, max 500, atomic

    # or mix operations:
    with ctx.batch() as batch:
        batch.save(city1)
        batch.update(city2, {"population": 1_000_000})
        batch.delete(city3)
    ```

---

## Transactions

=== "NDB (deprecated)"

    ```python
    @ndb.transactional
    def transfer():
        sf = City.get_by_id("SF")
        la = City.get_by_id("LA")
        sf.population -= 1000
        la.population += 1000
        ndb.put_multi([sf, la])

    transfer()
    ```

=== "Firestore SDK"

    ```python
    from google.cloud.firestore_v1.transaction import transactional

    transaction = client.transaction()

    @transactional
    def transfer(transaction, from_ref, to_ref, amount):
        from_doc = transaction.get(from_ref).to_dict()
        to_doc = transaction.get(to_ref).to_dict()
        transaction.update(from_ref, {
            "population": from_doc["population"] - amount,
        })
        transaction.update(to_ref, {
            "population": to_doc["population"] + amount,
        })

    from_ref = client.collection("cities").document("SF")
    to_ref = client.collection("cities").document("LA")
    transfer(transaction, from_ref, to_ref, 1000)
    ```

=== "Cendry"

    ```python
    def transfer(txn):
        sf = txn.get(City, "SF")
        la = txn.get(City, "LA")
        txn.update(sf, {"population": sf.population - 1000})
        txn.update(la, {"population": la.population + 1000})

    ctx.transaction(transfer)
    ```

---

## Nested data (Maps)

=== "NDB (deprecated)"

    ```python
    class Mayor(ndb.Model):
        name = ndb.StringProperty()

    class City(ndb.Model):
        mayor = ndb.StructuredProperty(Mayor)

    city = City.get_by_id("SF")
    print(city.mayor.name)  # typed but no IDE support
    ```

=== "Firestore SDK"

    ```python
    doc = client.collection("cities").document("SF").get()
    data = doc.to_dict()
    mayor_name = data.get("mayor", {}).get("name")  # nested dict access
    ```

=== "Cendry"

    ```python
    city = ctx.get(City, "SF")
    print(city.mayor.name)  # typed Map, IDE autocomplete
    ```

---

## Optimistic locking

=== "NDB (deprecated)"

    NDB doesn't have built-in optimistic locking. You must use transactions for conflict resolution.

=== "Firestore SDK"

    ```python
    from google.cloud.firestore_v1._helpers import LastUpdateOption

    doc = client.collection("cities").document("SF").get()
    client.collection("cities").document("SF").update(
        {"population": 900_000},
        option=LastUpdateOption(doc.update_time),
    )
    ```

=== "Cendry"

    ```python
    city = ctx.get(City, "SF")
    ctx.update(city, {"population": 900_000}, if_unchanged=True)
    ```

---

## Summary

| Aspect | NDB (deprecated) | Firestore SDK | Cendry |
|--------|------------------|--------------|--------|
| **Database** | Datastore mode only | Native mode | Native mode |
| **Model layer** | `ndb.Model` — no type annotations | None — raw dicts | `Model` + `Field[T]` — typed |
| **Data access** | `instance.field` — untyped | `dict["field"]` — untyped | `instance.field` — typed |
| **Filters** | `City.state == "CA"` | `FieldFilter("state", "==", "CA")` | `City.state == "CA"` |
| **Partial update** | Not supported | `doc.update({...})` | `ctx.update(instance, {...})` |
| **Nested data** | `StructuredProperty` | Nested dicts | `Map` class — typed |
| **Optimistic lock** | Not supported | `LastUpdateOption(...)` | `if_unchanged=True` |
| **Async** | Not supported | `AsyncClient` | `AsyncCendry` |
| **IDE support** | Minimal | None | Full autocomplete + type checking |
| **Status** | Legacy — Datastore only | Active — low-level | Active — typed ODM |

---

## Complete feature matrix

Comprehensive feature-by-feature comparison. Green (✅) = supported, yellow (🔶) = partial, red (❌) = not supported.

### Model & Schema

| Feature | NDB | Firestore SDK | Cendry | Notes |
|---------|-----|---------------|--------|-------|
| Typed model classes | 🔶 `ndb.Model` (no annotations) | ❌ Raw dicts | ✅ `Model` + `Field[T]` | Cendry validates types at class definition |
| Nested structures | ✅ `StructuredProperty` | 🔶 Nested dicts | ✅ `Map` class | Cendry maps are typed with IDE support |
| Field defaults | ✅ `default=` | N/A | ✅ `field(default=)` | |
| Field aliases | ❌ | N/A | ✅ `field(alias=)` | Firestore name ≠ Python name |
| Enum fields | ❌ | ❌ Manual | ✅ `Field[MyEnum]` | Auto-converts by value or name |
| Repeated/list fields | ✅ `repeated=True` | ✅ Arrays | ✅ `Field[list[str]]` | |
| Computed properties | ✅ `ComputedProperty` | ❌ | ❌ | Derived read-only fields — not yet in Cendry |
| Expando (dynamic fields) | ✅ `Expando` | ✅ Any dict key | ❌ | Intentional — Cendry favors typed schemas |
| Property validators | ✅ `validator=fn` | ❌ | ❌ | Per-field validation callbacks — not yet in Cendry |
| Custom type handlers | ❌ | ❌ | ✅ `register_type()` | Serialize/deserialize custom types |
| Type validation at definition | ❌ | ❌ | ✅ `TypeRegistry` | Catches invalid types before runtime |

### Read Operations

| Feature | NDB | Firestore SDK | Cendry | Notes |
|---------|-----|---------------|--------|-------|
| Get by ID | ✅ `Model.get_by_id()` | ✅ `doc_ref.get()` | ✅ `ctx.get()` | Cendry raises `DocumentNotFoundError` |
| Find (None if missing) | ❌ Returns None | 🔶 Check `.exists` | ✅ `ctx.find()` | |
| Batch get | ✅ `ndb.get_multi()` | ✅ `client.get_all()` | ✅ `ctx.get_many()` | |
| Projection queries | ✅ `projection=[...]` | ✅ `select([...])` | ❌ | Fetch only specific fields — not yet in Cendry |
| Distinct queries | ✅ `distinct_on=[...]` | ✅ Supported | ❌ | Deduplicate results — not yet in Cendry |
| Collection groups | ❌ | ✅ `collection_group()` | ✅ `ctx.select_group()` | NDB doesn't have this concept |

### Query & Filtering

| Feature | NDB | Firestore SDK | Cendry | Notes |
|---------|-----|---------------|--------|-------|
| Python operators | ✅ `City.state == "CA"` | ❌ Strings only | ✅ `City.state == "CA"` | |
| Composite filters (AND/OR) | 🔶 AND only | ✅ `And`/`Or` | ✅ `And`/`Or` + `&`/`|` | |
| Chainable queries | ❌ | ❌ | ✅ `.filter().order_by().limit()` | Immutable query builder |
| Ordering | ✅ `.order()` | ✅ `.order_by()` | ✅ `.order_by(City.pop.desc())` | |
| Limit | ✅ `.fetch(limit)` | ✅ `.limit()` | ✅ `.limit()` | |
| Pagination | ✅ Cursor-based | ✅ Cursor-based | ✅ `.paginate(page_size)` | Cendry doesn't export cursor tokens yet |
| Count | ❌ Must fetch all | ✅ `.count()` | ✅ `.count()` | Firestore aggregation |
| Exists check | ❌ | ❌ Manual | ✅ `.exists()` | |
| First result | ❌ `.fetch(1)` | ❌ Manual | ✅ `.first()` | |
| Exactly one | ❌ | ❌ Manual | ✅ `.one()` | Raises if 0 or >1 |
| Copy-pasteable repr | ❌ | ❌ | ✅ | All queries produce valid Python repr |

### Write Operations

| Feature | NDB | Firestore SDK | Cendry | Notes |
|---------|-----|---------------|--------|-------|
| Save (upsert) | ✅ `entity.put()` | ✅ `doc_ref.set()` | ✅ `ctx.save()` | Returns doc ID |
| Create (insert only) | ❌ | ✅ `doc_ref.create()` | ✅ `ctx.create()` | Raises on duplicate |
| Partial update | ❌ Full overwrite | ✅ `doc_ref.update()` | ✅ `ctx.update()` | Dot-notation, transforms |
| Delete | ✅ `key.delete()` | ✅ `doc_ref.delete()` | ✅ `ctx.delete()` | `must_exist=` option |
| Refresh (re-fetch in-place) | ❌ | ❌ | ✅ `ctx.refresh()` | Mutates instance |
| Auto-generate ID | ✅ Automatic | ✅ `document()` | ✅ Auto + mutates `instance.id` | |
| Field validation on write | ❌ | ❌ | ✅ `validate_required_fields` | |
| Firestore transforms | N/A | ✅ `Increment`, etc. | ✅ Re-exported | `DELETE_FIELD`, `SERVER_TIMESTAMP`, etc. |

### Batch & Transactions

| Feature | NDB | Firestore SDK | Cendry | Notes |
|---------|-----|---------------|--------|-------|
| Batch writes | ✅ `ndb.put_multi()` | ✅ `WriteBatch` | ✅ `ctx.save_many()` / `ctx.batch()` | Max 500, atomic |
| Batch delete | ✅ `ndb.delete_multi()` | ✅ `WriteBatch` | ✅ `ctx.delete_many()` | |
| Mixed batch operations | ❌ | ✅ `WriteBatch` | ✅ `ctx.batch()` context manager | save + update + delete |
| Transactions | ✅ `@ndb.transactional` | ✅ `@transactional` | ✅ `ctx.transaction(fn)` | Auto-retry on contention |
| Transaction context manager | ❌ | ❌ | ✅ `with ctx.transaction():` | Single attempt |
| Transaction reads | ✅ Implicit | ✅ `transaction.get()` | ✅ `txn.get()` / `txn.find()` | |
| Read-only transactions | ❌ | ✅ `read_only=True` | ✅ `read_only=True` | |

### Metadata & Concurrency

| Feature | NDB | Firestore SDK | Cendry | Notes |
|---------|-----|---------------|--------|-------|
| Document metadata | ❌ | ✅ `DocumentSnapshot` attrs | ✅ `get_metadata()` | `update_time`, `create_time` |
| Optimistic locking | ❌ Use transactions | ✅ `LastUpdateOption` | ✅ `if_unchanged=True` | Precondition-based |
| Real-time listeners | ❌ | ✅ `on_snapshot()` | ❌ | Live updates — different paradigm |

### Async Support

| Feature | NDB | Firestore SDK | Cendry | Notes |
|---------|-----|---------------|--------|-------|
| Async client | ❌ | ✅ `AsyncClient` | ✅ `AsyncCendry` | |
| Async reads | ❌ | ✅ | ✅ | `await ctx.get()` |
| Async writes | ❌ | ✅ | ✅ | `await ctx.save()` |
| Async queries | ❌ | ✅ `async for` | ✅ `async for` | |
| Async batch | ❌ | ✅ `AsyncWriteBatch` | ✅ `AsyncBatch` | |
| Async transactions | ❌ | ✅ `AsyncTransaction` | ✅ `AsyncTxn` | |

### Developer Experience

| Feature | NDB | Firestore SDK | Cendry | Notes |
|---------|-----|---------------|--------|-------|
| IDE autocomplete | 🔶 Minimal | ❌ | ✅ Full | `@dataclass_transform` |
| Type checking (mypy/ty) | ❌ | 🔶 Partial stubs | ✅ Strict | Both mypy and ty pass |
| Context manager | ❌ | ✅ | ✅ | Auto-closes client |
| Subcollections | ❌ Different model | ✅ Nested refs | ✅ `parent=` parameter | |
| Custom type handlers | ❌ | ❌ | ✅ `register_type()` | Pluggable serialize/deserialize |
| Model hooks | ✅ `_pre_put_hook`, etc. | ❌ | ❌ | Lifecycle callbacks — not yet in Cendry |

---

## What Cendry doesn't have (yet)

Features from NDB or the Firestore SDK that Cendry could add in future versions:

| Feature | Origin | Description | Effort |
|---------|--------|-------------|--------|
| Computed properties | NDB | Read-only fields derived from other fields | Medium |
| Model hooks | NDB | `_pre_save`, `_post_save`, `_pre_delete`, `_post_delete` callbacks | Medium |
| Property validators | NDB | `field(validator=fn)` for per-field validation | Medium |
| Projection queries | Both | Fetch only specific fields | Medium |
| Cursor export | Both | Expose pagination cursor tokens for stateless paging | Low |
| `allocate_ids()` | Both | Pre-allocate document IDs | Low |
| Real-time listeners | SDK | `on_snapshot()` for live updates | Hard |
| Expando models | Both | Dynamic properties not in schema | Medium |
| Distinct queries | Both | Deduplicate results | Low |

!!! info "Intentional differences"
    Some NDB features are intentionally **not** in Cendry:

    - **`Model.query()`** — Cendry uses the context as entry point, not the model class
    - **`PickleProperty` / `GenericProperty`** — anti-pattern for document databases
    - **Datastore mode** — Cendry targets Firestore Native mode only
