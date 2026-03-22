# Write, Update, and Delete

Single-document operations: save, create, update, delete, refresh, and optimistic locking.

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

### Class+ID form

When using the class+ID form (no instance), pass a `datetime` directly:

```python
import datetime

ctx.update(City, "SF", {"population": 900_000}, if_unchanged=some_datetime)
ctx.delete(City, "SF", if_unchanged=some_datetime)
```

## Subcollections

All single-document write operations support `parent=` for subcollections:

```python
ctx.save(neighborhood, parent=city)
ctx.update(neighborhood, {"population": 65_000}, parent=city)
ctx.delete(neighborhood, parent=city)
```

## Async

All operations have async equivalents:

```python
async with AsyncCendry() as ctx:
    await ctx.save(city)
    await ctx.create(city)
    await ctx.update(city, {"population": 900_000})
    await ctx.delete(city)
    await ctx.refresh(city)
```
