# Serialization

## from_dict

Construct a model instance from a raw dictionary. Useful for testing and data import.

```python
from cendry import from_dict

city = from_dict(City, {
    "name": "San Francisco",
    "state": "CA",
    "country": "USA",
    "capital": False,
    "population": 870_000,
    "regions": ["west_coast"],
})

# With document ID
city = from_dict(City, {...}, doc_id="SF")
print(city.id)  # "SF"
```

### Nested Maps

Nested `Map` dicts are automatically converted:

```python
city = from_dict(City, {
    "name": "SF",
    ...,
    "mayor": {"name": "London Breed", "since": 2018},
})
assert isinstance(city.mayor, Mayor)
```

### Missing Fields

Raises `TypeError` with a clear message if required fields are missing:

```python
from_dict(City, {"name": "SF"})
# TypeError: from_dict(City): missing required fields: state, country, capital, population, regions
```

### Aliases

By default, `from_dict` uses Python field names:

```python
city = from_dict(City, {"name": "SF"})            # Python names (default)
city = from_dict(City, {"displayName": "SF"}, by_alias=True)  # Firestore names
```

## to_dict

Convert a model instance to a dictionary:

```python
from cendry import to_dict

data = to_dict(city)
# {"name": "SF", "state": "CA", ...}
```

### Options

```python
to_dict(city)                         # Python field names (default)
to_dict(city, by_alias=True)          # Firestore field names (aliases)
to_dict(city, include_id=True)        # Include the document ID
```

### Nested Maps

Nested `Map` instances are recursively converted to dicts:

```python
data = to_dict(city)
print(data["mayor"])  # {"name": "London Breed", "since": 2018}
```

## Exceptions

```python
from cendry import CendryError, DocumentNotFoundError

try:
    city = ctx.get(City, "NOPE")
except DocumentNotFoundError as e:
    print(e.collection)     # "cities"
    print(e.document_id)    # "NOPE"
```

- `CendryError` — base exception for all Cendry errors
- `DocumentNotFoundError` — raised by `get()`, `get_many()`, and `Query.one()` when documents are not found
