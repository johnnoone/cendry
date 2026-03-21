# How to Filter and Query

## Python operators

```python
City.state == "CA"
City.population > 1_000_000
City.population <= 500_000
City.state != "NY"
```

## Named methods

For operators without a Python symbol:

```python
City.regions.array_contains("west_coast")
City.regions.array_contains_any(["west_coast", "east_coast"])
City.country.is_in(["USA", "Japan"])
City.country.not_in(["China"])
```

## Compose with & and |

```python
(City.state == "CA") & (City.population > 1_000_000)
(City.state == "CA") | (City.state == "NY")
```

Or explicitly:

```python
from cendry import And, Or

Or(
    City.state == "CA",
    And(City.country == "Japan", City.population > 1_000_000),
)
```

## Chain filters on Query

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

For raw Firestore filters:

```python
from cendry import FieldFilter

ctx.select(City, FieldFilter("state", "==", "CA"))
```

## Operators reference

| Operator | Python | Method |
|----------|--------|--------|
| `==` | `City.state == "CA"` | `City.state.eq("CA")` |
| `!=` | `City.state != "CA"` | `City.state.ne("CA")` |
| `>` | `City.pop > 100` | `City.pop.gt(100)` |
| `>=` | `City.pop >= 100` | `City.pop.gte(100)` |
| `<` | `City.pop < 100` | `City.pop.lt(100)` |
| `<=` | `City.pop <= 100` | `City.pop.lte(100)` |
| `array-contains` | — | `.array_contains(v)` |
| `array-contains-any` | — | `.array_contains_any([...])` |
| `in` | — | `.is_in([...])` |
| `not-in` | — | `.not_in([...])` |
