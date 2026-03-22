# Async with Cendry

In this tutorial, you'll learn how to use Cendry with `async`/`await`. By the end, you'll know how to read, write, query, and transact asynchronously.

!!! note "Prerequisites"
    Complete [First Steps](first-steps.md) first. You should also be familiar with Python's `async`/`await` syntax.

## Why async?

Async is useful when your application needs to handle many concurrent I/O operations — web servers, APIs, background workers. Instead of blocking while waiting for Firestore, async lets your app do other work.

Cendry's async API mirrors the sync API exactly — same models, same methods, just with `await`.

## Setup

```python
from cendry import AsyncCendry, Model, Field

class City(Model, collection="cities"):
    name: Field[str]
    state: Field[str]
    population: Field[int]
```

The model is the same — no async-specific changes needed.

## Connect with `AsyncCendry`

```python
async with AsyncCendry() as ctx:
    # all operations here are async
    ...
```

Or with a custom client:

```python
from google.cloud.firestore import AsyncClient

async with AsyncCendry(client=AsyncClient(project="my-project")) as ctx:
    ...
```

## Read documents

```python
async with AsyncCendry() as ctx:
    # Get by ID (raises DocumentNotFoundError)
    city = await ctx.get(City, "SF")
    print(city.name)

    # Find by ID (returns None if missing)
    city = await ctx.find(City, "SF")

    # Batch fetch
    cities = await ctx.get_many(City, ["SF", "LA", "NYC"])
```

## Query documents

Queries return `AsyncQuery` — iterate with `async for`:

```python
async with AsyncCendry() as ctx:
    # Async iteration
    async for city in ctx.select(City, City.state == "CA"):
        print(city.name)

    # Chainable — same API as sync
    query = (
        ctx.select(City)
        .filter(City.population > 1_000_000)
        .order_by(City.population.desc())
        .limit(5)
    )

    # Convenience methods are all awaitable
    cities = await query.to_list()
    first = await query.first()
    count = await query.count()
    exists = await query.exists()

    # Async pagination
    async for page in query.paginate(page_size=10):
        process(page)
```

!!! tip
    `ctx.select()` itself is **not** async — it returns an `AsyncQuery` synchronously. Only iteration and convenience methods (`to_list`, `first`, `count`, etc.) are async.

## Write documents

```python
async with AsyncCendry() as ctx:
    # Save (upsert)
    city = City(name="SF", state="CA", population=870_000)
    doc_id = await ctx.save(city)

    # Create (insert only)
    doc_id = await ctx.create(city)

    # Partial update
    await ctx.update(city, {"population": 900_000})

    # Delete
    await ctx.delete(city)

    # Refresh
    await ctx.refresh(city)
```

## Batch writes

```python
async with AsyncCendry() as ctx:
    # Convenience methods
    await ctx.save_many([city1, city2, city3])
    await ctx.delete_many([city1, city2])

    # Batch context manager
    async with ctx.batch() as batch:
        batch.save(city1)        # sync — queues the operation
        batch.create(city2)      # sync
        batch.update(city3, {"population": 1_000_000})  # sync
        batch.delete(city4)      # sync
    # commits on exit (async)
```

!!! info "Batch methods are sync"
    `batch.save()`, `batch.create()`, etc. are **synchronous** — they queue operations on the Firestore `WriteBatch`. Only the commit (on `async with` exit) is async.

## Transactions

```python
async with AsyncCendry() as ctx:
    # Callback pattern (auto-retry)
    async def transfer(txn):
        sf = await txn.get(City, "SF")    # async read
        la = await txn.get(City, "LA")    # async read
        txn.update(sf, {"population": sf.population - 1000})  # sync queue
        txn.update(la, {"population": la.population + 1000})  # sync queue

    await ctx.transaction(transfer)
    await ctx.transaction(transfer, max_attempts=10)

    # Context manager (single attempt)
    async with ctx.transaction() as txn:
        city = await txn.get(City, "SF")
        txn.update(city, {"population": city.population + 1000})
```

!!! info "Transaction reads are async, writes are sync"
    `txn.get()` and `txn.find()` are `async` (they execute Firestore RPCs). Write methods (`txn.save()`, `txn.update()`, etc.) are sync — they queue operations for the commit.

## Sync vs async — what changes?

| Operation | Sync | Async |
|-----------|------|-------|
| Context | `Cendry()` | `AsyncCendry()` |
| Context manager | `with ctx:` | `async with ctx:` |
| Reads | `ctx.get(...)` | `await ctx.get(...)` |
| Writes | `ctx.save(...)` | `await ctx.save(...)` |
| Query iteration | `for city in query:` | `async for city in query:` |
| Query convenience | `query.to_list()` | `await query.to_list()` |
| Batch commit | `with ctx.batch():` | `async with ctx.batch():` |
| Transaction callback | `ctx.transaction(fn)` | `await ctx.transaction(fn)` |
| Transaction context | `with ctx.transaction():` | `async with ctx.transaction():` |
| Model definition | Same | Same |
| Batch queue methods | Same (sync) | Same (sync) |

## Running async code

If you're not in an async context (e.g., a script), use `asyncio.run()`:

```python
import asyncio
from cendry import AsyncCendry

async def main():
    async with AsyncCendry() as ctx:
        city = await ctx.get(City, "SF")
        print(city.name)

asyncio.run(main())
```

## What's next?

- [How-To: Use Async](../how-to/async.md) — more async recipes
- [API Reference: AsyncCendry](../reference/context.md) — full method signatures
