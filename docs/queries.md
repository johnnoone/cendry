# Queries

## Context

All queries go through a context — `Cendry` (sync) or `AsyncCendry` (async):

```python
from cendry import Cendry, AsyncCendry

# Sync
with Cendry() as ctx:
    city = ctx.get(City, "SF")

# Async
async with AsyncCendry() as ctx:
    city = await ctx.get(City, "SF")
```

Both support context managers (`with`/`async with`) that close the Firestore client on exit. They also work without `with`.

## get

Fetch a single document by ID. Raises `DocumentNotFoundError` if not found.

```python
city = ctx.get(City, "SF")
```

## find

Like `get`, but returns `None` instead of raising.

```python
city = ctx.find(City, "SF")
if city is None:
    print("Not found")
```

## get_many

Batch fetch multiple documents by ID. Single Firestore round trip.

```python
cities = ctx.get_many(City, ["SF", "LA", "NYC"])
```

Raises `DocumentNotFoundError` if any ID is missing (error includes all missing IDs). Returns documents in the same order as input IDs.

## select

Query documents with filters. Returns a `Query` object.

```python
query = ctx.select(City, City.state == "CA", limit=10)

# Iterate
for city in query:
    print(city.name)
```

See [Filters](filters.md) for filtering options.

### Query Object

`select()` returns a `Query[T]` (sync) or `AsyncQuery[T]` (async) with chainable methods:

```python
cities = (
    ctx.select(City)
    .filter(City.state == "CA")
    .order_by(City.population.desc())
    .limit(10)
    .to_list()
)
```

#### Convenience Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `to_list()` | `list[T]` | Fetch all matching documents |
| `first()` | `T \| None` | First document, or `None` |
| `one()` | `T` | Exactly one document (raises otherwise) |
| `exists()` | `bool` | Whether any documents match |
| `count()` | `int` | Count via Firestore aggregation (no doc fetch) |

#### filter()

Add more filters to the query:

```python
query = ctx.select(City).filter(City.state == "CA").filter(City.population > 500_000)

# Also accepts a list (implicit AND)
query = ctx.select(City).filter([City.state == "CA", City.population > 500_000])
```

`filter()` returns a new `Query` — queries are immutable.

#### order_by()

```python
# Ascending (default)
query = ctx.select(City).order_by(City.population)

# Descending
query = ctx.select(City).order_by(City.population.desc())

# Multiple orderings (append)
query = ctx.select(City).order_by(City.state, City.name.desc())
```

#### limit()

```python
query = ctx.select(City).limit(10)
```

#### paginate()

Iterate over pages of results:

```python
for page in ctx.select(City).paginate(page_size=10):
    print(f"Got {len(page)} cities")
    for city in page:
        print(city.name)
```

Each page is a `list[T]`. Stops when a page has fewer items than `page_size`.

### Async

All Query methods have async counterparts:

```python
cities = await ctx.select(City).filter(City.state == "CA").to_list()
city = await ctx.select(City).first()

async for page in ctx.select(City).paginate(page_size=10):
    process(page)
```

## select_group

Query across all subcollections with the same name (Firestore collection group query):

```python
# All "neighborhoods" across all cities
for n in ctx.select_group(Neighborhood, Neighborhood.population > 50_000):
    print(n.name)
```

Returns the same `Query` object with all the same methods.

## Subcollections

Use the `parent=` parameter to query a subcollection under a specific document:

```python
city = ctx.get(City, "SF")

# Get neighborhoods under SF
for n in ctx.select(Neighborhood, parent=city):
    print(n.name)

# Also works with get and get_many
n = ctx.get(Neighborhood, "MISSION", parent=city)
```

## Ordering and Pagination Parameters

`select()` also accepts ordering and pagination as keyword arguments:

```python
from cendry import Asc, Desc

ctx.select(City,
    City.state == "CA",
    order_by=[Asc(City.population), Desc(City.name)],
    limit=10,
    start_after={"population": 1_000_000},
)
```

Cursor parameters: `start_at`, `start_after`, `end_at`, `end_before` — accept `dict` or `Model` instance.
