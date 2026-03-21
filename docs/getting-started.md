# Getting Started

## Installation

```bash
pip install cendry
```

Or with uv:

```bash
uv add cendry
```

## Requirements

- Python >= 3.13
- A Google Cloud project with Firestore enabled

## Quick Example

```python
from cendry import Model, Map, Field, field, Cendry

# Define your models
class Mayor(Map):
    name: Field[str]
    since: Field[int]

class City(Model, collection="cities"):
    name: Field[str]
    state: Field[str]
    country: Field[str]
    capital: Field[bool]
    population: Field[int]
    regions: Field[list[str]]
    nickname: Field[str | None] = field(default=None)
    mayor: Field[Mayor | None] = field(default=None)

# Query Firestore
with Cendry() as ctx:
    # Get a single document
    city = ctx.get(City, "SF")
    print(city.name, city.population)

    # Query with filters
    for city in ctx.select(City, City.state == "CA", limit=10):
        print(city.name)

    # Batch fetch
    cities = ctx.get_many(City, ["SF", "LA", "NYC"])
```

## Async Support

```python
from cendry import AsyncCendry

async with AsyncCendry() as ctx:
    city = await ctx.get(City, "SF")

    async for city in ctx.select(City, City.state == "CA"):
        print(city.name)
```

## Custom Client

By default, Cendry uses Application Default Credentials. You can pass a custom Firestore client:

```python
from google.cloud.firestore import Client

ctx = Cendry(client=Client(project="my-project", database="my-db"))
```
