# Cendry

**A typed Firestore ODM for Python.** Define models, query with Python operators, get full IDE support.

```bash
pip install cendry
```

---

## Define once, query naturally

=== "Model"

    ```python
    from cendry import Model, Map, Field, field

    class Mayor(Map):
        name: Field[str]
        since: Field[int]

    class City(Model, collection="cities"):
        name: Field[str]
        state: Field[str]
        population: Field[int]
        mayor: Field[Mayor | None] = field(default=None)
    ```

=== "Query"

    ```python
    from cendry import Cendry

    with Cendry() as ctx:
        # Python operators become Firestore filters
        cities = (
            ctx.select(City)
            .filter(City.state == "CA")
            .order_by(City.population.desc())
            .limit(10)
            .to_list()
        )

        for city in cities:
            print(city.name, city.population)
    ```

=== "Write"

    ```python
    from cendry import Cendry, Increment

    with Cendry() as ctx:
        # Save (upsert)
        city = City(name="SF", state="CA", population=870_000)
        ctx.save(city)  # auto-generates ID

        # Partial update
        ctx.update(city, {"population": Increment(1000)})

        # Atomic batch
        with ctx.batch() as batch:
            batch.save(city1)
            batch.delete(city2)

        # Transaction with auto-retry
        def transfer(txn):
            src = txn.get(City, "SF")
            txn.update(src, {"population": src.population - 100})

        ctx.transaction(transfer)
    ```

=== "Async"

    ```python
    from cendry import AsyncCendry

    async with AsyncCendry() as ctx:
        city = await ctx.get(City, "SF")
        print(city.name)

        await ctx.save(city)
        await ctx.update(city, {"population": 900_000})

        async for city in ctx.select(City, City.state == "CA"):
            print(city.population)
    ```

---

## What is Firestore?

[Cloud Firestore](https://firebase.google.com/docs/firestore) is a NoSQL document database from Google — serverless, scalable, strongly consistent. Cendry is a **typed ODM** (Object-Document Mapper) that lets you work with Firestore using Python classes instead of raw dicts. [Learn more →](explanation/firestore.md)

## Why Cendry?

<div class="grid" markdown>

**Type-safe from definition to query.** `Field[T]` annotations are validated at class definition time. Your IDE knows every field, every filter method, every return type.

**Python operators, not strings.** Write `City.population > 1_000_000` instead of `FieldFilter("population", ">", 1000000)`. Compose with `&` and `|`.

**Sync and async.** Same API, same models. `Cendry` for sync, `AsyncCendry` for async. Powered by anyio — works with asyncio and trio.

**Thin wrapper, not an abstraction.** Cendry doesn't hide Firestore. `FieldFilter` is Firestore's own class. Query semantics match Firestore exactly.

</div>

---

## Features at a glance

| Feature | Example |
|---------|---------|
| **Typed models** | `name: Field[str]` — validated at class definition |
| **Python filters** | `City.state == "CA"` — operators become Firestore filters |
| **Chainable queries** | `.filter(...).order_by(...).limit(10).to_list()` |
| **Pagination** | `for page in query.paginate(page_size=20):` |
| **Batch fetch** | `ctx.get_many(City, ["SF", "LA", "NYC"])` |
| **Field aliases** | `field(alias="displayName")` — Python name ≠ Firestore name |
| **Enum support** | `Field[Status]` — auto-converts by value or name |
| **Write operations** | `ctx.save(city)`, `ctx.create(city)`, `ctx.update(city, {...})`, `ctx.delete(city)` |
| **Batch writes** | `ctx.save_many([...])`, `with ctx.batch() as b:` — atomic, max 500 |
| **Transactions** | `ctx.transaction(fn)` — auto-retry, read-then-write atomicity |
| **Optimistic locking** | `ctx.update(city, {...}, if_unchanged=True)` — precondition-based |
| **Serialization** | `from_dict(City, {...})` and `to_dict(city)` |
| **Custom types** | `register_type(Money, deserialize=...)` |
| **Context manager** | `with Cendry() as ctx:` — auto-closes client |

---

## Get started

<div markdown>

**New to Cendry?** Start with the [First Steps tutorial](tutorials/first-steps.md) — install, define a model, run your first query in 5 minutes.

**Know what you need?** Jump to a [How-To Guide](how-to/index.md) — practical recipes for models, filtering, aliases, async, and more.

**Looking for specifics?** Check the [API Reference](reference/index.md) — every class, method, and parameter documented.

**Want to understand the design?** Read the [Explanation](explanation/index.md) — architecture and design decisions.

</div>

---

<div markdown style="text-align: center; color: #888; font-size: 0.9em;">

Python >= 3.13 · Built on [google-cloud-firestore](https://pypi.org/project/google-cloud-firestore/) and [anyio](https://pypi.org/project/anyio/) · [GitHub](https://github.com/johnnoone/cendry)

</div>
