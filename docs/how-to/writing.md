# Write, Update, and Delete

Save, create, update, delete, batch, and transact — everything you need to write data.

---

## Save (upsert)

```python
city = City(name="SF", state="CA", country="USA", capital=False, population=870_000, regions=[])

# Auto-generates an ID and mutates city.id
doc_id = ctx.save(city)
print(city.id)  # "auto-generated-id"

# Overwrites with the existing ID
city.population = 900_000
ctx.save(city)
```

`save` uses Firestore's `set()` — insert or overwrite.

## Create (insert only)

```python
doc_id = ctx.create(city)
```

Raises `DocumentAlreadyExistsError` if the document already exists. The original Firestore `Conflict` is preserved as `__cause__`.

## Update (partial)

Update specific fields without overwriting the entire document:

```python
ctx.update(city, {"population": 900_000})

# By class + ID (no need to fetch first)
ctx.update(City, "SF", {"population": 900_000})

# Dot-notation for nested fields
ctx.update(city, {"mayor.name": "Jane"})
```

### Firestore transforms

```python
from cendry import DELETE_FIELD, SERVER_TIMESTAMP, Increment, ArrayUnion

ctx.update(city, {
    "population": Increment(1000),
    "tags": ArrayUnion(["major-city"]),
    "updated_at": SERVER_TIMESTAMP,
    "deprecated_field": DELETE_FIELD,
})
```

All Firestore sentinels and transforms are re-exported from `cendry`.

!!! warning
    `update` raises `DocumentNotFoundError` if the document doesn't exist. Use `save` for upsert semantics.

## Delete

```python
ctx.delete(city)                          # by instance
ctx.delete(City, "SF")                    # by class + ID
ctx.delete(City, "SF", must_exist=True)   # raises DocumentNotFoundError if missing
```

## Refresh

Re-fetch a document from Firestore and update the instance in-place:

```python
ctx.update(city, {"population": Increment(1000)})
ctx.refresh(city)
print(city.population)  # updated value from Firestore
```

## Batch writes

Atomic multi-document writes (max 500 operations):

```python
# Convenience methods
ctx.save_many([city1, city2, city3])
ctx.delete_many([city1, city2])
ctx.delete_many(City, ["SF", "LA"])

# Full control with batch context manager
with ctx.batch() as batch:
    batch.save(city1)
    batch.create(city2)
    batch.update(city3, {"population": 1_000_000})
    batch.delete(city4)
# auto-commits on exit, discards on exception
```

!!! tip
    `save_many` and `delete_many` raise `CendryError` if more than 500 items are passed. Split large batches yourself to control atomicity boundaries.

## Transactions

Read-then-write atomicity with automatic retry on contention:

### Callback pattern (recommended)

```python
def transfer(txn):
    from_city = txn.get(City, "SF")
    to_city = txn.get(City, "LA")
    txn.update(from_city, {"population": from_city.population - 1000})
    txn.update(to_city, {"population": to_city.population + 1000})

ctx.transaction(transfer)
ctx.transaction(transfer, max_attempts=10)
```

The callback is retried automatically on contention (up to `max_attempts`, default 5).

### Context manager (single attempt)

```python
with ctx.transaction() as txn:
    city = txn.get(City, "SF")
    txn.update(city, {"population": city.population + 1000})
```

!!! warning
    The context manager does **not** retry on contention. Use the callback pattern for critical operations.

### Transaction reads

Reads inside a transaction see a consistent snapshot:

```python
def my_txn(txn):
    city = txn.get(City, "SF")        # raises DocumentNotFoundError
    city = txn.find(City, "SF")       # returns None if missing
```

## Async

All write operations have async equivalents:

```python
async with AsyncCendry() as ctx:
    await ctx.save(city)
    await ctx.create(city)
    await ctx.update(city, {"population": 900_000})
    await ctx.delete(city)
    await ctx.refresh(city)
    await ctx.save_many([city1, city2])
    await ctx.delete_many([city1, city2])

    # Async transaction
    async def transfer(txn):
        city = await txn.get(City, "SF")
        txn.update(city, {"population": city.population + 1000})

    await ctx.transaction(transfer)

    # Async batch
    async with ctx.batch() as batch:
        batch.save(city1)
        batch.delete(city2)
```

## Optimistic locking

Prevent conflicting writes with `if_unchanged` — Cendry checks the document hasn't been modified since you read it:

```python
from cendry import get_metadata

city = ctx.get(City, "SF")

# ... time passes, another client might modify the doc ...

# This fails if the document changed since we read it
ctx.update(city, {"population": 900_000}, if_unchanged=True)
ctx.delete(city, if_unchanged=True)
```

Under the hood, Cendry tracks Firestore's `update_time` metadata automatically on every read and write. `if_unchanged=True` passes a precondition to Firestore — the write is rejected atomically if the document changed.

!!! tip "Check metadata"
    Use `get_metadata(instance)` to inspect `update_time` and `create_time`:
    ```python
    meta = get_metadata(city)
    print(meta.update_time)  # datetime from Firestore
    ```

!!! warning "Batch writes don't track metadata"
    Batch operations don't populate metadata. Refresh instances after a batch if you need optimistic locking:
    ```python
    with ctx.batch() as batch:
        batch.save(city1)
        batch.save(city2)

    ctx.refresh(city1)  # now metadata is available
    ctx.refresh(city2)
    ctx.update(city1, {"population": 900_000}, if_unchanged=True)
    ```

### Class+ID form

When using the class+ID form (no instance), pass a `datetime` directly:

```python
import datetime

ctx.update(City, "SF", {"population": 900_000}, if_unchanged=some_datetime)
ctx.delete(City, "SF", if_unchanged=some_datetime)
```

## Subcollections

All write operations support `parent=` for subcollections:

```python
ctx.save(neighborhood, parent=city)
ctx.update(neighborhood, {"population": 65_000}, parent=city)
ctx.delete(neighborhood, parent=city)
ctx.save_many([nb1, nb2], parent=city)
```
