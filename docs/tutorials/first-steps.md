# First Steps

This tutorial walks you through installing Cendry, defining your first model, and reading data from Firestore.

## Prerequisites

- Python >= 3.13
- A Google Cloud project with Firestore enabled
- Application Default Credentials configured (`gcloud auth application-default login`)

## Install Cendry

```bash
pip install cendry
```

## Define a Model

A **Model** maps to a Firestore collection. Each field is annotated with `Field[T]`.

```python
from cendry import Model, Map, Field, field

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
```

!!! info "Key concepts"

    - `Model` — a top-level Firestore document, bound to a collection.
    - `Map` — embedded data (a Firestore map within a document). No collection, no `id`.
    - `Field[T]` — a typed field. On instances it returns the value; on the class it provides filter methods.
    - All fields are **keyword-only**.

## Connect and Query

Use `Cendry` as a context manager:

```python
from cendry import Cendry

with Cendry() as ctx:
    # Fetch a single document by ID
    city = ctx.get(City, "SF")
    print(city.name, city.population)

    # Find returns None instead of raising
    maybe = ctx.find(City, "UNKNOWN")
    print(maybe)  # None
```

## Iterate Over Results

```python
with Cendry() as ctx:
    for city in ctx.select(City, City.state == "CA"):
        print(f"{city.name}: {city.population}")
```

`select()` returns a `Query` object — it streams results lazily from Firestore.

## Batch Fetch

```python
with Cendry() as ctx:
    cities = ctx.get_many(City, ["SF", "LA", "NYC"])
    for city in cities:
        print(city.name)
```

## What's Next?

- Learn about [querying, filtering, and pagination](querying.md)
- See the [how-to guides](../how-to/index.md) for specific tasks
