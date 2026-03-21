# How to Use Async

Cendry supports async via `AsyncCendry` and `AsyncQuery`, powered by anyio (works with both asyncio and trio).

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

## Custom async client

```python
from google.cloud.firestore import AsyncClient

ctx = AsyncCendry(client=AsyncClient(project="my-project"))
```

!!! note

    `AsyncCendry.select()` and `AsyncCendry.select_group()` are **not** `async def` —
    they return an `AsyncQuery` synchronously. Only the terminal methods (`to_list()`,
    `first()`, etc.) and iteration are async.
