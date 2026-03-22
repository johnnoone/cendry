# Writing Data

In this tutorial, you'll learn how to save, update, and delete documents using Cendry. By the end, you'll know how to perform all CRUD operations, batch writes, and transactions.

!!! note "Prerequisites"
    Complete [First Steps](first-steps.md) first — you'll need a model and a context.

## Save your first document

```python
from cendry import Cendry, Model, Field

class City(Model, collection="cities"):
    name: Field[str]
    state: Field[str]
    population: Field[int]

with Cendry() as ctx:
    city = City(name="San Francisco", state="CA", population=870_000)
    doc_id = ctx.save(city)

    print(city.id)   # Firestore auto-generated an ID
    print(doc_id)    # same value, also returned
```

`save` is an **upsert** — it creates the document if it doesn't exist, or overwrites it if it does. If `city.id` is `None`, Firestore generates a unique ID and Cendry sets it on the instance.

## Update specific fields

Instead of overwriting the whole document, update only what changed:

```python
ctx.update(city, {"population": 900_000})
```

You can also update without fetching first:

```python
ctx.update(City, "SF", {"population": 900_000})
```

### Firestore transforms

Cendry re-exports Firestore's transform values:

```python
from cendry import Increment, SERVER_TIMESTAMP, DELETE_FIELD

ctx.update(city, {
    "population": Increment(1000),      # atomic increment
    "updated_at": SERVER_TIMESTAMP,     # server timestamp
    "old_field": DELETE_FIELD,          # remove field
})
```

## Delete a document

```python
# By instance
ctx.delete(city)

# By class + ID
ctx.delete(City, "SF")
```

## Refresh after update

Since `update` doesn't mutate the local instance, use `refresh` to re-fetch:

```python
ctx.update(city, {"population": Increment(1000)})
ctx.refresh(city)
print(city.population)  # now reflects the server value
```

## Batch writes

Save or delete many documents in one atomic operation (max 500):

```python
cities = [
    City(name="SF", state="CA", population=870_000),
    City(name="LA", state="CA", population=3_900_000),
    City(name="NYC", state="NY", population=8_300_000),
]

ctx.save_many(cities)
# All three now have auto-generated IDs
```

For mixed operations, use the batch context manager:

```python
with ctx.batch() as batch:
    batch.save(new_city)
    batch.update(existing_city, {"population": 1_000_000})
    batch.delete(old_city)
# All operations commit atomically on exit
```

!!! warning
    If any operation in the batch fails, **all** operations are rolled back.

## Transactions

When you need to read data and then write based on what you read — atomically:

```python
def transfer_population(txn):
    sf = txn.get(City, "SF")
    la = txn.get(City, "LA")

    txn.update(sf, {"population": sf.population - 1000})
    txn.update(la, {"population": la.population + 1000})

ctx.transaction(transfer_population)
```

If another client modifies the same documents, Firestore automatically retries the transaction (up to 5 times by default):

```python
ctx.transaction(transfer_population, max_attempts=10)
```

## Async

All write operations have async equivalents:

```python
from cendry import AsyncCendry

async with AsyncCendry() as ctx:
    await ctx.save(city)
    await ctx.update(city, {"population": 900_000})
    await ctx.delete(city)
    await ctx.refresh(city)
    await ctx.save_many(cities)

    async def my_txn(txn):
        city = await txn.get(City, "SF")
        txn.update(city, {"population": city.population + 1000})

    await ctx.transaction(my_txn)
```

## What's next?

- [How-To: Write, Update, and Delete](../how-to/writing.md) — recipes for specific write patterns
- [API Reference: Context](../reference/context.md) — full method signatures
