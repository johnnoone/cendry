# Querying Data

This tutorial covers filtering, ordering, pagination, and the Query object.

## Filtering

Use Python operators directly on field descriptors:

```python
with Cendry() as ctx:
    # Equality
    for city in ctx.select(City, City.state == "CA"):
        print(city.name)

    # Comparison
    big_cities = ctx.select(City, City.population > 1_000_000).to_list()

    # Multiple filters (implicit AND)
    results = ctx.select(
        City,
        City.state == "CA",
        City.population > 500_000,
    ).to_list()
```

### Firestore-specific operators

Some operators don't have a Python symbol:

```python
ctx.select(City, City.regions.array_contains("west_coast"))
ctx.select(City, City.country.is_in(["USA", "Japan"]))
```

### Composing filters

Use `&` (AND) and `|` (OR):

```python
query = ctx.select(
    City,
    (City.state == "CA") | (City.state == "NY"),
)
```

!!! warning "Operator precedence"

    Always use parentheses: `(City.state == "CA") & (City.population > 100)`.
    Without parentheses, `&` binds tighter than `==` in Python.

## The Query Object

`select()` returns a `Query` — an immutable, chainable query builder:

```python
query = (
    ctx.select(City)
    .filter(City.state == "CA")
    .filter(City.population > 500_000)
    .order_by(City.population.desc())
    .limit(10)
)
```

### Terminal methods

| Method | Returns | Description |
|--------|---------|-------------|
| `to_list()` | `list[T]` | Fetch all results |
| `first()` | `T \| None` | First result |
| `one()` | `T` | Exactly one (raises otherwise) |
| `exists()` | `bool` | Any results? |
| `count()` | `int` | Count via aggregation |

```python
cities = query.to_list()
first_city = query.first()
total = query.count()
```

### Iterating

```python
for city in query:
    print(city.name)
```

## Ordering

```python
# Ascending (default)
query = ctx.select(City).order_by(City.population)

# Descending
query = ctx.select(City).order_by(City.population.desc())

# Multiple orderings
query = ctx.select(City).order_by(City.state, City.name.desc())
```

## Pagination

Iterate over pages of results:

```python
for page in ctx.select(City).paginate(page_size=20):
    print(f"Page with {len(page)} cities")
    for city in page:
        process(city)
```

Each page is a `list[T]`. The iterator stops when a page has fewer items than `page_size`.

## Subcollections

Query documents nested under a parent:

```python
city = ctx.get(City, "SF")
for n in ctx.select(Neighborhood, parent=city):
    print(n.name)
```

## Collection Groups

Query across all subcollections with the same name:

```python
for n in ctx.select_group(Neighborhood, Neighborhood.population > 50_000):
    print(n.name)
```

## Debugging

All filter and query objects have copy-pasteable `repr`:

```python
>>> City.state == "CA"
City.state == 'CA'

>>> ctx.select(City).filter(City.state == "CA").order_by(City.population).limit(10)
Query(City, City.state == 'CA', order_by=[City.population.asc()], limit=10)
```
