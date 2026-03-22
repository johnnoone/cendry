# Reference

Technical reference for every class, function, and parameter in Cendry. Everything is importable from `cendry`:

```python
from cendry import (
    # Models
    Model, Map, Field, field, FieldDescriptor,
    # Context
    Cendry, AsyncCendry,
    # Query
    Query, AsyncQuery, Asc, Desc,
    # Batch & Transactions
    Batch, AsyncBatch, Txn, AsyncTxn,
    # Filters
    FieldFilter, And, Or,
    # Firestore sentinels & transforms
    DELETE_FIELD, SERVER_TIMESTAMP,
    Increment, ArrayUnion, ArrayRemove, Maximum, Minimum,
    # Serialization
    from_dict, to_dict,
    # Type system
    TypeHandler, BaseTypeHandler, TypeRegistry, register_type,
    # Exceptions
    CendryError, DocumentNotFoundError, DocumentAlreadyExistsError,
)
```

---

**[Models](models.md)** · **[Context](context.md)** · **[Query](query.md)** · **[Filters](filters.md)** · **[Serialization](serialization.md)** · **[Types](types.md)** · **[Exceptions](exceptions.md)**
