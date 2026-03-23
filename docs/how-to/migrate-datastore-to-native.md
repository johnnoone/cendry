# Migrate from Datastore to Native Mode

Move your app from Firestore in Datastore mode to Firestore in Native mode, using Cendry as the bridge.

---

## Prerequisites

- A GCP project running Firestore in **Datastore mode**
- Python >= 3.13
- Docker (for testing with emulators)

Install Cendry with Datastore support:

=== "pip"

    ```bash
    pip install cendry[datastore]
    ```

=== "uv"

    ```bash
    uv add cendry[datastore]
    ```

## Step 1: Define your models

Map your existing Datastore Kinds to Cendry `Model` classes. Use the **same Kind name** as the `collection=` value — this name is shared between Datastore mode and Native mode.

```python
from cendry import Cendry, Field, Model, field


class City(Model, collection="City"):
    name: Field[str]
    state: Field[str]
    population: Field[int]
    capital: Field[bool]
    tags: Field[list[str]] = field(default_factory=list)
```

!!! info "Collection naming"
    `collection=` is used as the Datastore **Kind** name and later as the Firestore **collection** name. Pick one convention and stick with it.

## Step 2: Validate with Datastore backend

Connect Cendry to your existing Datastore data and verify models deserialize correctly.

```python
from cendry import Cendry
from cendry.backends.datastore import DatastoreBackend

backend = DatastoreBackend(project="my-gcp-project")
db = Cendry(backend=backend)

# Read existing entities
cities = db.select(City).to_list()
for city in cities:
    print(f"{city.name} ({city.state}): pop {city.population}")

# Fetch by ID
sf = db.get(City, "SF")
print(sf.name)  # San Francisco
```

!!! tip "Test with the Datastore emulator first"
    Before pointing at production data, test with a local emulator:

    ```bash
    gcloud beta emulators datastore start --project=test
    export DATASTORE_EMULATOR_HOST=localhost:8081
    ```

## Step 3: Run your app on Datastore backend

Replace your existing data access layer with Cendry. Your app logic uses the same Cendry API regardless of backend — `get`, `save`, `select`, `batch`, `transaction` all work.

```python
# All the same API — only the backend changes
db.save(City(name="Portland", state="OR", population=650000, capital=False))

with db.batch() as b:
    b.save(city1)
    b.save(city2)

results = db.select(City, City.state == "CA").to_list()
```

!!! warning "TOCTOU race on `create()` and `update()`"
    Datastore has no atomic "create if not exists" or partial update. On the Datastore backend:

    - `create()` checks existence then writes — **not atomic** outside transactions
    - `update()` fetches, merges, then writes — **not atomic** outside transactions

    Wrap these calls in transactions for safety:

    ```python
    def safe_create(txn):
        txn.save(City(id="SF", name="San Francisco", ...))

    db.transaction(safe_create)
    ```

### Feature differences

Not all Cendry features are available on the Datastore backend:

| Feature | Datastore | Native |
|---|---|---|
| CRUD (get, save, delete, update) | Yes | Yes |
| Queries (filter, order, limit) | Yes | Yes |
| AND filters | Yes | Yes |
| OR filters | No | Yes |
| Batch writes | Yes | Yes |
| Transactions | Yes | Yes |
| Subcollections / parent | Yes (ancestor keys) | Yes |
| Collection group queries | No | Yes |
| Real-time listeners (`on_snapshot`) | No | Yes |
| Async (`AsyncCendry`) | No | Yes |
| Transforms (`Increment`, `SERVER_TIMESTAMP`) | No | Yes |
| Optimistic locking (`if_unchanged`) | No | Yes |
| Document metadata (`update_time`, `create_time`) | No | Yes |

Unsupported features raise a `CendryError` with a message guiding you to migrate.

## Step 4: Migrate the database

Use Google's built-in migration tool to convert your database from Datastore mode to Native mode.

!!! warning "This is a one-way, irreversible operation"
    Once migrated, you **cannot** go back to Datastore mode. Test thoroughly with emulators before migrating production.

1. Go to the [Cloud Console → Firestore](https://console.cloud.google.com/firestore)
2. Click **"Upgrade to Firestore in Native mode"**
3. Follow the prompts

See [Google's migration documentation](https://cloud.google.com/datastore/docs/upgrade-to-firestore) for details.

## Step 5: Switch to Firestore backend

One line change:

```python
# Before (Datastore mode)
from cendry.backends.datastore import DatastoreBackend

db = Cendry(backend=DatastoreBackend(project="my-gcp-project"))

# After (Native mode)
db = Cendry()  # uses FirestoreBackend by default
```

All your models, queries, and app logic stay exactly the same.

## Step 6: Unlock Native-only features

Now you can use everything Cendry offers:

```python
from cendry import AsyncCendry, Increment, SERVER_TIMESTAMP

# Async support
async with AsyncCendry() as db:
    city = await db.get(City, "SF")

# Real-time listeners
watch = db.on_snapshot(City, "SF", lambda instance, changes, time: ...)

# Collection group queries
all_neighborhoods = db.select_group(Neighborhood).to_list()

# Transforms
db.update(city, {"population": Increment(1000)})

# Optimistic locking
db.update(city, {"name": "SF"}, if_unchanged=True)
```
