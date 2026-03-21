# How to Use Async

Cendry supports async via `AsyncCendry` and `AsyncQuery`, powered by anyio — works with both asyncio and trio.

## Async context

```python
from cendry import AsyncCendry

async with AsyncCendry() as ctx:
    city = await ctx.get(City, "SF")
    city = await ctx.find(City, "SF")
    cities = await ctx.get_many(City, ["SF", "LA"])
```

## Async queries

`select()` returns `AsyncQuery` — same chainable API, async terminal methods:

```python
async with AsyncCendry() as ctx:
    cities = await ctx.select(City, City.state == "CA").to_list()
    first = await ctx.select(City).first()
    count = await ctx.select(City).count()
```

## Async iteration

```python
async for city in ctx.select(City, City.state == "CA"):
    print(city.name)
```

## Async pagination

```python
async for page in ctx.select(City).paginate(page_size=20):
    for city in page:
        process(city)
```

## Chainable filtering and ordering

Same as sync — `filter()`, `order_by()`, and `limit()` are synchronous methods that return `AsyncQuery`:

```python
query = (
    ctx.select(City)
    .filter(City.state == "CA")
    .order_by(City.population.desc())
    .limit(10)
)

# Only terminal methods are async
cities = await query.to_list()
```

## Custom async client

```python
from google.cloud.firestore import AsyncClient

ctx = AsyncCendry(client=AsyncClient(project="my-project"))
```

!!! note "select() is not async"

    `AsyncCendry.select()` and `AsyncCendry.select_group()` are regular `def` methods — they return an `AsyncQuery` synchronously. Only terminal methods (`to_list()`, `first()`, etc.) and iteration are async.

!!! tip "Same models, same filters"

    Models, fields, and filters are shared between sync and async. You define them once and use them with either `Cendry` or `AsyncCendry`.
