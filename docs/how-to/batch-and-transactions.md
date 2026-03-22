# Batch Writes and Transactions

Multi-document atomic operations: batch writes, save_many/delete_many, and transactions.

---

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

### Batch methods

The `Batch` object supports the same methods as the context:

| Method | Description |
|--------|-------------|
| `batch.save(instance)` | Queue upsert, mutates `instance.id` if None |
| `batch.create(instance)` | Queue insert-only |
| `batch.update(instance, {...})` | Queue partial update |
| `batch.update(Class, id, {...})` | Queue partial update by class + ID |
| `batch.delete(instance)` | Queue delete |
| `batch.delete(Class, id)` | Queue delete by class + ID |

All methods support `parent=` for subcollections.

### Batch + optimistic locking

Batch writes don't populate metadata. Refresh instances after a batch if you need optimistic locking:

```python
with ctx.batch() as batch:
    batch.save(city1)
    batch.save(city2)

ctx.refresh(city1)  # now metadata is available
ctx.refresh(city2)
ctx.update(city1, {"population": 900_000}, if_unchanged=True)
```

## Transactions

Read-then-write atomicity with automatic retry on contention.

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

### Transaction writes

The `Txn` object supports the same write methods as `Batch`:

| Method | Description |
|--------|-------------|
| `txn.save(instance)` | Queue upsert |
| `txn.create(instance)` | Queue insert-only |
| `txn.update(instance, {...})` | Queue partial update |
| `txn.delete(instance)` | Queue delete |

### Read-only transactions

For read-only workloads (no writes), use `read_only=True` for better performance:

```python
def report(txn):
    sf = txn.get(City, "SF")
    la = txn.get(City, "LA")
    return sf.population + la.population

total = ctx.transaction(report, read_only=True)
```

## Async

All batch and transaction operations have async equivalents:

```python
async with AsyncCendry() as ctx:
    await ctx.save_many([city1, city2])
    await ctx.delete_many([city1, city2])

    # Async batch
    async with ctx.batch() as batch:
        batch.save(city1)
        batch.delete(city2)

    # Async transaction
    async def transfer(txn):
        city = await txn.get(City, "SF")
        txn.update(city, {"population": city.population + 1000})

    await ctx.transaction(transfer)
```

## Subcollections

All batch and transaction operations support `parent=` for subcollections:

```python
ctx.save_many([nb1, nb2], parent=city)

with ctx.batch() as batch:
    batch.save(neighborhood, parent=city)

def my_txn(txn):
    nb = txn.get(Neighborhood, "MISSION", parent=city)
    txn.update(nb, {"population": 65_000}, parent=city)

ctx.transaction(my_txn)
```
