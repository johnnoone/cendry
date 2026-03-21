# How to Filter and Query

## Python operators

The most natural way to filter — use Python comparison operators directly:

```python
City.state == "CA"
City.population > 1_000_000
City.population <= 500_000
City.state != "NY"
```

## Named methods

For Firestore operators that don't have a Python symbol:

```python
City.regions.array_contains("west_coast")
City.regions.array_contains_any(["west_coast", "east_coast"])
City.country.is_in(["USA", "Japan"])
City.country.not_in(["China"])
```

!!! tip "Explicit equivalents"

    Every operator also has a named method: `.eq()`, `.ne()`, `.gt()`, `.gte()`, `.lt()`, `.lte()`. Useful when you need to pass the method as a callback.

## Compose with & and |

```python
(City.state == "CA") & (City.population > 1_000_000)
(City.state == "CA") | (City.state == "NY")
```

Or use `And` / `Or` explicitly:

```python
from cendry import And, Or

Or(
    City.state == "CA",
    And(City.country == "Japan", City.population > 1_000_000),
)
```

!!! warning "Use parentheses"

    `&` and `|` have higher precedence than `==` in Python. Always wrap comparisons in parentheses.

## Chain filters on Query

Build up filters incrementally — each call returns a new immutable `Query`:

```python
query = (
    ctx.select(City)
    .filter(City.state == "CA")
    .filter(City.population > 500_000)
)
```

Also accepts a list:

```python
query = ctx.select(City).filter([
    City.state == "CA",
    City.population > 500_000,
])
```

## Use FieldFilter directly

For raw Firestore filters when you need them:

```python
from cendry import FieldFilter

ctx.select(City, FieldFilter("state", "==", "CA"))
```

## Operators reference

| Operator | Python | Method |
|----------|--------|--------|
| `==` | `City.state == "CA"` | `.eq("CA")` |
| `!=` | `City.state != "CA"` | `.ne("CA")` |
| `>` | `City.pop > 100` | `.gt(100)` |
| `>=` | `City.pop >= 100` | `.gte(100)` |
| `<` | `City.pop < 100` | `.lt(100)` |
| `<=` | `City.pop <= 100` | `.lte(100)` |
| `array-contains` | — | `.array_contains(v)` |
| `array-contains-any` | — | `.array_contains_any([...])` |
| `in` | — | `.is_in([...])` |
| `not-in` | — | `.not_in([...])` |
