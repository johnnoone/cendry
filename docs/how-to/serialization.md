# How to Serialize Data

## Create models from dicts

`from_dict` constructs model instances from raw dictionaries — useful for testing and data import.

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

Raises `TypeError` with a clear message listing all missing fields:

```python
from_dict(City, {"name": "SF"})
# TypeError: from_dict(City): missing required fields: state, country, ...
```

## Convert models to dicts

```python
from cendry import to_dict

data = to_dict(city)
# {"name": "San Francisco", "state": "CA", ...}
```

### Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `by_alias` | `False` | Use Firestore alias keys instead of Python names |
| `include_id` | `False` | Include the document ID in the output |

```python
to_dict(city, include_id=True)
# {"name": "San Francisco", ..., "id": "SF"}

to_dict(city, by_alias=True)
# {"displayName": "San Francisco", ...}
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

!!! tip "Custom types in tests"

    If your model uses a registered custom type (like `Money`), `from_dict` runs the handler's `deserialize` automatically — your tests get the same conversion as production.
