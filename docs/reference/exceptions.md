# Exceptions Reference

## `CendryError`

Base exception for all Cendry errors.

```python
from cendry import CendryError
```

## `DocumentNotFoundError`

Raised when a document is not found.

```python
from cendry import DocumentNotFoundError
```

**Raised by:** `get()`, `get_many()`, `Query.one()`

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `collection` | `str` | Collection name |
| `document_id` | `str` | Document ID (or comma-separated IDs for `get_many`) |

```python
try:
    city = ctx.get(City, "NOPE")
except DocumentNotFoundError as e:
    print(e.collection)     # "cities"
    print(e.document_id)    # "NOPE"
```
