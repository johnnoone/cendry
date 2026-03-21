# Querying Data

This tutorial covers everything you need to query Firestore effectively: filtering with Python operators, chaining queries, ordering, pagination, and debugging.

## Filtering

Use Python operators directly on field descriptors — no strings, no magic:

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

Some operators don't have a Python symbol. Use the named methods:

```python
ctx.select(City, City.regions.array_contains("west_coast"))
ctx.select(City, City.country.is_in(["USA", "Japan"]))
ctx.select(City, City.country.not_in(["China"]))
```

### Composing filters

Use `&` (AND) and `|` (OR) to combine:

```python
query = ctx.select(
    City,
    (City.state == "CA") | (City.state == "NY"),
)
```

!!! warning "Operator precedence"

    Always use parentheses with `&` and `|`:

    ```python
    # Correct
    (City.state == "CA") & (City.population > 100)

    # Wrong — & binds tighter than == in Python
    City.state == "CA" & City.population > 100
    ```

## The Query Object

`select()` returns a `Query` — an immutable, chainable query builder. Every method returns a new `Query`, so it's safe to reuse and compose.

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

These execute the query and return results:

| Method | Returns | Description |
|--------|---------|-------------|
| `to_list()` | `list[T]` | Fetch all results |
| `first()` | `T \| None` | First result, or None |
| `one()` | `T` | Exactly one (raises otherwise) |
| `exists()` | `bool` | Any results? |
| `count()` | `int` | Count via Firestore aggregation |

```python
cities = query.to_list()
first_city = query.first()
total = query.count()
```

!!! tip "Reusable queries"

    `Query` objects are reusable. Each terminal method creates a fresh Firestore stream, so you can call `to_list()` and then `count()` on the same query.

### Iterating

Queries are iterable — they stream results lazily:

```python
for city in query:
    print(city.name)
```

### Adding more filters

`filter()` accepts individual filters, multiple filters, or a list:

```python
# Individual
query = ctx.select(City).filter(City.state == "CA")

# Multiple (implicit AND)
query = ctx.select(City).filter(City.state == "CA", City.population > 100)

# List
query = ctx.select(City).filter([City.state == "CA", City.population > 100])
```

## Ordering

```python
# Ascending (default when passing a field descriptor)
query = ctx.select(City).order_by(City.population)

# Descending
query = ctx.select(City).order_by(City.population.desc())

# Multiple orderings — they append
query = ctx.select(City).order_by(City.state, City.name.desc())
```

!!! tip

    Prefer `City.population.asc()` and `City.population.desc()` over importing `Asc`/`Desc` — fewer imports.

## Pagination

Iterate over pages of results. Each page is a `list[T]`:

```python
for page in ctx.select(City).paginate(page_size=20):
    print(f"Page with {len(page)} cities")
    for city in page:
        process(city)
```

The iterator stops automatically when a page has fewer items than `page_size`.

## Subcollections

Query documents nested under a parent using `parent=`:

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

All filter and query objects have **copy-pasteable repr** — what you see in the debugger is valid Python you can paste back:

```python
>>> City.state == "CA"
City.state == 'CA'

>>> City.population.desc()
City.population.desc()

>>> ctx.select(City).filter(City.state == "CA").order_by(City.population).limit(10)
Query(City, City.state == 'CA', order_by=[City.population.asc()], limit=10)
```

!!! tip "Design principle"

    This is intentional — see [Design Decisions](../explanation/design-decisions.md#copy-pasteable-repr) for why.
