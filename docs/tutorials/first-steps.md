# First Steps

In this tutorial you'll install Cendry, define your first model, and read data from Firestore. By the end, you'll be querying documents with full type safety.

## Prerequisites

- Python >= 3.13
- A Google Cloud project with Firestore enabled
- Application Default Credentials configured (`gcloud auth application-default login`)

## Install Cendry

=== "pip"

    ```bash
    pip install cendry
    ```

=== "uv"

    ```bash
    uv add cendry
    ```

## Define a Model

A **Model** maps to a Firestore collection. Each field uses `Field[T]` for type-safe annotations.

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

    - **`Model`** — a top-level Firestore document, bound to a collection.
    - **`Map`** — embedded data (a Firestore map within a document). No collection, no `id`.
    - **`Field[T]`** — a typed field. On instances it returns the value; on the class it provides filter methods.
    - All fields are **keyword-only** — you write `City(name="SF", state="CA")`.

!!! tip "Invalid types are caught early"

    If you use a type Firestore doesn't support, like `Field[complex]`, you'll get a `TypeError` at class definition — not at query time.

## Connect and Query

Use `Cendry` as a context manager. It closes the Firestore client automatically.

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

!!! tip "Custom client"

    By default, Cendry uses Application Default Credentials. Pass a custom client for specific projects:

    ```python
    from google.cloud.firestore import Client
    ctx = Cendry(client=Client(project="my-project"))
    ```

## Iterate Over Results

`select()` returns a `Query` — it streams results lazily from Firestore.

```python
with Cendry() as ctx:
    for city in ctx.select(City, City.state == "CA"):
        print(f"{city.name}: {city.population}")
```

Notice `City.state == "CA"` — that's a real Python expression that creates a Firestore filter. No strings needed.

## Batch Fetch

Fetch multiple documents in a single round trip:

```python
with Cendry() as ctx:
    cities = ctx.get_many(City, ["SF", "LA", "NYC"])
    for city in cities:
        print(city.name)
```

!!! warning

    `get_many` raises `DocumentNotFoundError` if any ID is missing. The error includes all missing IDs.

## What's Next?

You've covered the basics. Next steps:

- **[Querying Data](querying.md)** — filters, ordering, pagination, the Query object
- **[How-To Guides](../how-to/index.md)** — recipes for specific tasks
