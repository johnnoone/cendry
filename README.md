# Cendry

A Firestore ODM for Python. Typed models, composable filters, sync and async support.

Built on top of [google-cloud-firestore](https://pypi.org/project/google-cloud-firestore/) and [anyio](https://pypi.org/project/anyio/).

**Python >= 3.13** | **Read-only (v1)**

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

### Query Documents

#### Sync

```python
from cendry import Cendry

context = Cendry()

# Get by ID (raises DocumentNotFound if missing)
city = context.get(City, "SF")

# Find by ID (returns None if missing)
city = context.find(City, "SF")

# Select with filters
for city in context.select(City, City.state.eq("CA"), limit=10):
    print(city.name)
```

#### Async

```python
from cendry import AsyncCendry

context = AsyncCendry()

city = await context.get(City, "SF")
city = await context.find(City, "SF")

async for city in context.select(City, City.state.eq("CA")):
    print(city.name)
```

### Custom Client

```python
from google.cloud.firestore import Client, AsyncClient

context = Cendry(client=Client(project="my-project"))
context = AsyncCendry(client=AsyncClient(project="my-project"))
```

## Filters

### FieldFilter (Firestore-native)

```python
from cendry import FieldFilter

context.select(City, FieldFilter("state", "==", "CA"))
context.select(City, FieldFilter("regions", "array-contains", "west_coast"))
context.select(City, FieldFilter("country", "in", ["USA", "Japan"]))
```

Operators: `<`, `<=`, `==`, `>`, `>=`, `!=`, `array-contains`, `array-contains-any`, `in`, `not-in`

### Field Descriptors (typed)

```python
City.state.eq("CA")
City.state.ne("CA")
City.population.gt(1000000)
City.population.gte(1000000)
City.population.lt(500000)
City.population.lte(500000)
City.regions.array_contains("west_coast")
City.regions.array_contains_any(["west_coast", "east_coast"])
City.country.is_in(["USA", "Japan"])
City.country.not_in(["China"])
```

### Composition

```python
# & (AND) and | (OR)
City.state.ne("CA") & City.population.gt(1000000)
City.state.eq("CA") | (City.country.eq("Japan") & City.population.gt(1000000))

# Explicit
from cendry import And, Or

Or(
    City.state.eq("CA"),
    And(City.country.eq("Japan"), City.population.gt(1000000)),
)

# Multiple varargs — implicit AND
context.select(City, City.state.eq("CA"), City.population.gt(1000000))
```

## Ordering and Pagination

```python
from cendry import Asc, Desc

context.select(City,
    City.state.eq("CA"),
    order_by=[Asc(City.population), Desc(City.name)],
    limit=10,
    start_after={"population": 1000000},
)
```

Pagination cursors: `start_at`, `start_after`, `end_at`, `end_before` — accept `dict` or `Model` instance.

## Subcollections

```python
class Neighborhood(Model, collection="neighborhoods"):
    name: Field[str]
    population: Field[int]

city = context.get(City, "SF")
for n in context.select(Neighborhood, parent=city):
    print(n.name)
```

## Collection Groups

```python
# Query across all "neighborhoods" subcollections
for n in context.select_group(Neighborhood, Neighborhood.population.gt(50000)):
    print(n.name)
```

## Exceptions

```python
from cendry import CendryError, DocumentNotFound

try:
    city = context.get(City, "NOPE")
except DocumentNotFound as e:
    print(e.collection, e.document_id)
```

## License

MIT
