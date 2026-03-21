# How to Use Field Aliases

When the Firestore field name differs from the Python attribute name.

## Define an alias

```python
from cendry import Model, Field, field

class City(Model, collection="cities"):
    name: Field[str] = field(alias="displayName")
    state: Field[str]
```

## What aliases affect

- **Filters:** `City.name == "SF"` generates `FieldFilter("displayName", ...)`.
- **Ordering:** `City.name.asc()` sorts by `"displayName"` in Firestore.
- **Deserialization:** `ctx.get(City, "SF")` reads from the `"displayName"` key.
- **`to_dict` / `from_dict`:** configurable via `by_alias`.

## Serialization with aliases

```python
from cendry import to_dict, from_dict

city = ctx.get(City, "SF")

# Python field names (default)
to_dict(city)                    # {"name": "SF", ...}

# Firestore field names
to_dict(city, by_alias=True)     # {"displayName": "SF", ...}

# from_dict: Python names by default
from_dict(City, {"name": "SF", "state": "CA"})

# from_dict with Firestore names
from_dict(City, {"displayName": "SF", "state": "CA"}, by_alias=True)
```

## No alias = no change

Fields without `alias=` use the Python name in Firestore. This is backwards compatible.
