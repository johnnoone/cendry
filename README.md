# Cendry

A Firestore ODM for Python. Typed models, composable filters, sync and async support.

Built on top of [google-cloud-firestore](https://pypi.org/project/google-cloud-firestore/) and [anyio](https://pypi.org/project/anyio/).

**Python >= 3.13**

## Installation

```bash
pip install cendry
```

## Quick Start

### Define Models

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

- `Model` — top-level Firestore document, requires `collection=`
- `Map` — embedded data (Firestore map), no collection, no `id`
- `Field[T]` — typed field descriptor
- Every `Model` has an `id: str | None` field (Firestore document ID)
- All fields are keyword-only

### Query Documents

#### Sync

```python
from cendry import Cendry

with Cendry() as ctx:
    # Get by ID (raises DocumentNotFoundError if missing)
    city = ctx.get(City, "SF")

    # Find by ID (returns None if missing)
    city = ctx.find(City, "SF")

    # Select with filters
    for city in ctx.select(City, City.state == "CA", limit=10):
        print(city.name)
```

#### Async

```python
from cendry import AsyncCendry

async with AsyncCendry() as ctx:
    city = await ctx.get(City, "SF")
    city = await ctx.find(City, "SF")

    async for city in ctx.select(City, City.state == "CA"):
        print(city.name)
```

### Custom Client

```python
from google.cloud.firestore import Client, AsyncClient

ctx = Cendry(client=Client(project="my-project"))
ctx = AsyncCendry(client=AsyncClient(project="my-project"))
```

## Filters

### FieldFilter (Firestore-native)

```python
from cendry import FieldFilter

ctx.select(City, FieldFilter("state", "==", "CA"))
ctx.select(City, FieldFilter("regions", "array-contains", "west_coast"))
ctx.select(City, FieldFilter("country", "in", ["USA", "Japan"]))
```

Operators: `<`, `<=`, `==`, `>`, `>=`, `!=`, `array-contains`, `array-contains-any`, `in`, `not-in`

### Field Descriptors

Python operators work directly:

```python
City.state == "CA"
City.state != "CA"
City.population > 1_000_000
City.population >= 1_000_000
City.population < 500_000
City.population <= 500_000
```

Named methods for Firestore-specific operators:

```python
City.regions.array_contains("west_coast")
City.regions.array_contains_any(["west_coast", "east_coast"])
City.country.is_in(["USA", "Japan"])
City.country.not_in(["China"])
```

### Composition

```python
# & (AND) and | (OR)
City.state != "CA" & City.population > 1_000_000
City.state == "CA" | (City.country == "Japan" & City.population > 1_000_000)

# Explicit
from cendry import And, Or

Or(
    City.state == "CA",
    And(City.country == "Japan", City.population > 1_000_000),
)

# Multiple varargs — implicit AND
ctx.select(City, City.state == "CA", City.population > 1_000_000)
```

## Query Object

`select()` and `select_group()` return a `Query` (sync) or `AsyncQuery` (async) with convenience methods:

```python
query = ctx.select(City, City.state == "CA")

# Iterate (streaming)
for city in query:
    print(city.name)

# Chainable filtering
query = ctx.select(City).filter(City.state == "CA").filter(City.population > 500_000)

# Also accepts a list
query = ctx.select(City).filter([City.state == "CA", City.population > 500_000])

# Chainable ordering and limiting
query = (
    ctx.select(City)
    .filter(City.state == "CA")
    .order_by(City.population)           # ascending by default
    .order_by(City.name.desc())          # descending
    .limit(10)
)

# Convenience methods
cities = query.to_list()      # list[City]
city = query.first()          # City | None
city = query.one()            # City (raises if not exactly 1)
exists = query.exists()       # bool
n = query.count()             # int (Firestore aggregation)

# Pagination
for page in query.paginate(page_size=10):
    print(f"Got {len(page)} cities")
```

Async:

```python
cities = await query.to_list()
city = await query.first()
n = await query.count()

async for page in query.paginate(page_size=10):
    process(page)
```

## Write Operations

### Save (upsert)

```python
city = City(name="SF", state="CA", country="USA", capital=False, population=870_000, regions=[])
doc_id = ctx.save(city)  # auto-generates ID, mutates city.id
print(city.id)           # "auto-generated-id"

city.population = 900_000
ctx.save(city)           # overwrites with explicit ID
```

### Create (insert only)

```python
from cendry import DocumentAlreadyExistsError

try:
    ctx.create(city)
except DocumentAlreadyExistsError:
    print("Already exists!")
```

### Update (partial)

```python
from cendry import DELETE_FIELD, SERVER_TIMESTAMP, Increment

# By instance
ctx.update(city, {"population": 900_000, "name": "San Francisco"})

# By class + ID
ctx.update(City, "SF", {"population": Increment(1000)})

# Dot-notation for nested fields
ctx.update(city, {"mayor.name": "Jane", "updated_at": SERVER_TIMESTAMP})
```

### Delete

```python
ctx.delete(city)                          # by instance
ctx.delete(City, "SF")                    # by class + ID
ctx.delete(City, "SF", must_exist=True)   # raises if missing
```

### Refresh

```python
ctx.update(city, {"population": Increment(1000)})
ctx.refresh(city)  # re-fetches from Firestore, mutates in-place
print(city.population)  # updated value
```

## Batch Writes

```python
# Save many (atomic, max 500)
ctx.save_many([city1, city2, city3])

# Delete many
ctx.delete_many([city1, city2])
ctx.delete_many(City, ["SF", "LA"])

# Mix operations with batch context manager
with ctx.batch() as batch:
    batch.save(city1)
    batch.create(city2)
    batch.update(city3, {"population": 1_000_000})
    batch.delete(city4)
# auto-commits on exit
```

## Transactions

```python
# Callback pattern (auto-retry on contention)
def transfer(txn):
    from_city = txn.get(City, "SF")
    to_city = txn.get(City, "LA")
    txn.update(from_city, {"population": from_city.population - 1000})
    txn.update(to_city, {"population": to_city.population + 1000})

ctx.transaction(transfer)

# Context manager (single attempt)
with ctx.transaction() as txn:
    city = txn.get(City, "SF")
    txn.update(city, {"population": city.population + 1000})
```

## Batch Fetch

```python
cities = ctx.get_many(City, ["SF", "LA", "NYC"])
```

Raises `DocumentNotFoundError` if any IDs are missing.

## Ordering and Pagination

```python
ctx.select(City,
    City.state == "CA",
    order_by=[City.population.asc(), City.name.desc()],
    limit=10,
    start_after={"population": 1_000_000},
)
```

Pagination cursors: `start_at`, `start_after`, `end_at`, `end_before` — accept `dict` or `Model` instance.

## Subcollections

```python
class Neighborhood(Model, collection="neighborhoods"):
    name: Field[str]
    population: Field[int]

city = ctx.get(City, "SF")
for n in ctx.select(Neighborhood, parent=city):
    print(n.name)
```

## Collection Groups

```python
for n in ctx.select_group(Neighborhood, Neighborhood.population > 50_000):
    print(n.name)
```

## from_dict

Construct models from raw dicts (useful for testing):

```python
from cendry import from_dict

city = from_dict(City, {
    "name": "SF", "state": "CA", "country": "USA",
    "capital": False, "population": 870_000, "regions": ["west"],
})

# With document ID
city = from_dict(City, {...}, doc_id="123")
```

Nested `Map` dicts are automatically converted. Raises `TypeError` if required fields are missing.

## to_dict

Convert models to dicts:

```python
from cendry import to_dict

data = to_dict(city)                    # Python field names
data = to_dict(city, by_alias=True)     # Firestore field names
data = to_dict(city, include_id=True)   # Include document ID
```

## Field Aliases

When the Firestore field name differs from Python:

```python
class City(Model, collection="cities"):
    name: Field[str] = field(alias="displayName")
```

Filters, ordering, and Firestore reads/writes use the alias automatically.

## Enum Support

```python
import enum

class Status(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class User(Model, collection="users"):
    status: Field[Status]
    role: Field[Role] = field(enum_by="name")  # store by name instead of value
```

## Type Validation

`Field[T]` annotations are validated at class definition time. Only Firestore-compatible types are accepted:

```python
from cendry import register_type

# Register custom types
register_type(MyCustomClass)
register_type(lambda cls: hasattr(cls, "__my_protocol__"))
```

Supported: `str`, `int`, `float`, `bool`, `bytes`, `Decimal`, `datetime`, `GeoPoint`, `DocumentReference`, `list`, `tuple`, `set`, `dict`, `Map`, dataclasses, `TypedDict`, `enum.Enum`, pydantic/attrs/msgspec (if installed).

## Optimistic Locking

Prevent conflicting writes — Cendry tracks Firestore's `update_time` metadata automatically:

```python
from cendry import get_metadata

city = ctx.get(City, "SF")
meta = get_metadata(city)
print(meta.update_time)  # datetime from Firestore

# Only update if nobody changed it since we read
ctx.update(city, {"population": 900_000}, if_unchanged=True)
ctx.delete(city, if_unchanged=True)

# Class+ID form — pass datetime directly
ctx.update(City, "SF", {"population": 900_000}, if_unchanged=some_datetime)
```

After batch writes, refresh to get metadata:

```python
with ctx.batch() as batch:
    batch.save(city1)
    batch.save(city2)

ctx.refresh(city1)  # now get_metadata(city1).update_time is set
ctx.update(city1, {"population": 900_000}, if_unchanged=True)
```

## Exceptions

```python
from cendry import CendryError, DocumentNotFoundError, DocumentAlreadyExistsError

try:
    city = ctx.get(City, "NOPE")
except DocumentNotFoundError as e:
    print(e.collection, e.document_id)

try:
    ctx.create(city)
except DocumentAlreadyExistsError as e:
    print(e.collection, e.document_id)
```

## License

MIT
