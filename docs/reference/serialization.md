# Serialization Reference

## `from_dict`

```python
from_dict(
    model_class: type[T],
    data: dict[str, Any],
    *,
    doc_id: str | None = None,
    by_alias: bool = False,
) -> T
```

Construct a model instance from a dict.

| Parameter | Description |
|-----------|-------------|
| `model_class` | The Model class to construct |
| `data` | Dict of field values |
| `doc_id` | Document ID (optional) |
| `by_alias` | If `True`, read keys by Firestore alias. Default `False` (Python names). |

Raises `TypeError` if required fields are missing.

## `to_dict`

```python
to_dict(
    instance: Model | Map,
    *,
    by_alias: bool = False,
    include_id: bool = False,
) -> dict[str, Any]
```

Convert a model/map instance to a dict.

| Parameter | Description |
|-----------|-------------|
| `instance` | Model or Map instance |
| `by_alias` | If `True`, use Firestore alias keys. Default `False` (Python names). |
| `include_id` | If `True`, include document ID. Default `False`. |
