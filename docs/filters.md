# Filters

## Python Operators

The simplest way to create filters — use Python comparison operators on field descriptors:

```python
City.state == "CA"
City.state != "CA"
City.population > 1_000_000
City.population >= 1_000_000
City.population < 500_000
City.population <= 500_000
```

## Named Methods

For Firestore-specific operators that have no Python equivalent:

```python
City.regions.array_contains("west_coast")
City.regions.array_contains_any(["west_coast", "east_coast"])
City.country.is_in(["USA", "Japan"])
City.country.not_in(["China"])
```

Explicit equivalents of the operators:

```python
City.state.eq("CA")      # ==
City.state.ne("CA")      # !=
City.population.gt(100)  # >
City.population.gte(100) # >=
City.population.lt(100)  # <
City.population.lte(100) # <=
```

## Composition

### & (AND) and | (OR)

```python
(City.state == "CA") & (City.population > 1_000_000)
(City.state == "CA") | (City.country == "Japan")
```

Note: use parentheses — `&` and `|` have higher precedence than `==` in Python.

### Explicit And / Or

```python
from cendry import And, Or

Or(
    City.state == "CA",
    And(City.country == "Japan", City.population > 1_000_000),
)
```

### Multiple Filters in select/filter

Multiple filters passed as arguments are implicitly AND'd:

```python
# These are equivalent
ctx.select(City, City.state == "CA", City.population > 500_000)
ctx.select(City).filter(City.state == "CA", City.population > 500_000)
ctx.select(City).filter([City.state == "CA", City.population > 500_000])
```

## FieldFilter (Firestore-native)

You can also use Firestore's `FieldFilter` directly:

```python
from cendry import FieldFilter

ctx.select(City, FieldFilter("state", "==", "CA"))
```

### Supported Operators

| Operator | Python | Named Method |
|----------|--------|-------------|
| `<` | `City.pop < 100` | `City.pop.lt(100)` |
| `<=` | `City.pop <= 100` | `City.pop.lte(100)` |
| `==` | `City.state == "CA"` | `City.state.eq("CA")` |
| `>` | `City.pop > 100` | `City.pop.gt(100)` |
| `>=` | `City.pop >= 100` | `City.pop.gte(100)` |
| `!=` | `City.state != "CA"` | `City.state.ne("CA")` |
| `array-contains` | — | `City.regions.array_contains("x")` |
| `array-contains-any` | — | `City.regions.array_contains_any([...])` |
| `in` | — | `City.country.is_in([...])` |
| `not-in` | — | `City.country.not_in([...])` |

## Debugging Filters

All filter objects have copy-pasteable `repr`:

```python
>>> City.state == "CA"
City.state == 'CA'

>>> City.regions.array_contains("west")
City.regions.array_contains('west')

>>> (City.state == "CA") & (City.population > 100)
And(City.state == 'CA', City.population > 100)
```
