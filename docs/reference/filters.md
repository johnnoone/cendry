# Filters Reference

## `FieldFilter`

Firestore's own filter class, re-exported from `google.cloud.firestore_v1`.

```python
FieldFilter("state", "==", "CA")
```

## `FieldFilterResult`

Produced by field descriptor methods and dunders. Carries the alias (for Firestore), operator, value, and owner class (for repr).

```python
>>> City.state == "CA"
City.state == 'CA'

>>> City.regions.array_contains("west")
City.regions.array_contains('west')
```

## `And`

Composite AND filter. Requires at least 2 filters.

```python
And(City.state == "CA", City.population > 100)
```

Also produced by `&`:

```python
(City.state == "CA") & (City.population > 100)
```

## `Or`

Composite OR filter. Requires at least 2 filters.

```python
Or(City.state == "CA", City.state == "NY")
```

Also produced by `|`:

```python
(City.state == "CA") | (City.state == "NY")
```

## `Filter`

Base class for composable filters. Provides `__and__` and `__or__`.
