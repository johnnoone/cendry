# How to Use Field Aliases

Use aliases when the Firestore field name differs from your Python attribute name.

## Define an alias

```python
from cendry import Model, Field, field

class City(Model, collection="cities"):
    name: Field[str] = field(alias="displayName")
    state: Field[str]  # no alias — "state" in Firestore
```

## What aliases affect

| Operation | Behavior |
|-----------|----------|
| **Filters** | `City.name == "SF"` generates `FieldFilter("displayName", ...)` |
| **Ordering** | `City.name.asc()` sorts by `"displayName"` in Firestore |
| **Deserialization** | `ctx.get(City, "SF")` reads from the `"displayName"` key |
| **`to_dict` / `from_dict`** | Configurable via `by_alias` parameter |

## Serialization with aliases

Python names are the default for `to_dict` and `from_dict` — use `by_alias=True` for Firestore names:

```python
from cendry import to_dict, from_dict

city = ctx.get(City, "SF")

# Python field names (default)
to_dict(city)                    # {"name": "SF", ...}

# Firestore field names
to_dict(city, by_alias=True)     # {"displayName": "SF", ...}
```

```python
# Python names (default)
from_dict(City, {"name": "SF", "state": "CA"})

# Firestore names
from_dict(City, {"displayName": "SF", "state": "CA"}, by_alias=True)
```

!!! info "Why Python names are the default"

    `from_dict` and `to_dict` are Python-facing APIs — you're working with Python code, so Python names make sense. Firestore-facing operations (reading documents, applying filters) always use aliases internally.

## No alias = no change

Fields without `alias=` use the Python name in Firestore. This is the default and is fully backwards compatible.
