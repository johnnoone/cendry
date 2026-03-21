# How to Serialize Data

## Create models from dicts

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
```

### With a document ID

```python
city = from_dict(City, {...}, doc_id="SF")
print(city.id)  # "SF"
```

### Nested Maps

Nested `Map` dicts are automatically converted:

```python
city = from_dict(City, {
    ...,
    "mayor": {"name": "London Breed", "since": 2018},
})
assert isinstance(city.mayor, Mayor)
```

### Missing fields

Raises `TypeError` with a clear message:

```python
from_dict(City, {"name": "SF"})
# TypeError: from_dict(City): missing required fields: state, country, ...
```

## Convert models to dicts

```python
from cendry import to_dict

data = to_dict(city)
# {"name": "San Francisco", "state": "CA", ...}

# Include document ID
to_dict(city, include_id=True)
# {"name": "San Francisco", ..., "id": "SF"}

# Use Firestore alias keys
to_dict(city, by_alias=True)
```

## Testing without Firestore

`from_dict` is the primary tool for testing — no mocks needed for model construction:

```python
def test_city_population():
    city = from_dict(City, {
        "name": "SF",
        "state": "CA",
        "country": "USA",
        "capital": False,
        "population": 870_000,
        "regions": [],
    })
    assert city.population == 870_000
```
