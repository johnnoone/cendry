# Work with Document IDs

Every Cendry `Model` has an `id` field (`str | None`) that maps to the Firestore document ID. This guide covers how IDs are assigned, what constraints apply, and best practices.

---

## Default behavior

By default, `id` is `None`. Firestore auto-generates an ID when you save:

```python
from cendry import Cendry, Model, Field

class City(Model, collection="cities"):
    name: Field[str]
    state: Field[str]

city = City(name="San Francisco", state="CA")
print(city.id)  # None

with Cendry() as ctx:
    ctx.save(city)
    print(city.id)  # "Lxl1B2qZ5r9Hx4K2m7pQ" (auto-generated)
```

## Manual IDs

Set `id` before saving when you need deterministic, meaningful document IDs:

```python
city = City(id="SF", name="San Francisco", state="CA")
ctx.save(city)
print(city.id)  # "SF"
```

Use manual IDs for:

- **Idempotent writes** — saving the same ID twice overwrites, not duplicates
- **Meaningful keys** — user email, slug, external system ID
- **Cross-reference** — when other documents need to reference this one by a known key

## Auto-generated IDs

When `id` is `None`, Firestore generates a random 20-character alphanumeric string. Cendry sets `instance.id` immediately — you can use it right after the call:

```python
city = City(name="Portland", state="OR")
ctx.save(city)
print(city.id)  # available immediately

# Also works in batch and transaction contexts:
with ctx.batch() as batch:
    city2 = City(name="Seattle", state="WA")
    batch.save(city2)
    print(city2.id)  # set during queueing, before commit
```

This applies to both `save()` and `create()`, in all contexts (`Cendry`, `AsyncCendry`, `Batch`, `AsyncBatch`, `Txn`, `AsyncTxn`).

## ID constraints

Firestore Native mode enforces these constraints on document IDs:

| Constraint | Detail |
|------------|--------|
| **Type** | `str` — strings only |
| **Max size** | 1,500 bytes |
| **Forbidden values** | `.` and `..` |
| **Forbidden characters** | `/` (forward slash) |
| **Encoding** | Valid UTF-8 |

!!! warning "Avoid monotonically increasing IDs"
    IDs like `user_001`, `user_002`, `user_003` cause **write hotspots** in Firestore. Sequential IDs concentrate writes on a small number of storage splits, degrading performance under load. Use random IDs or meaningful non-sequential keys instead.

## Native mode vs Datastore mode

!!! info "ID types differ between Firestore modes"
    **Native mode** (what Cendry targets) supports **string IDs only**.

    **Datastore mode** supports both **string names** and **64-bit integer IDs**, with optional auto-allocation of numeric IDs.

    Since Cendry targets Native mode, `id` is always `str | None`. See [Comparisons](../explanation/comparison.md#identity) for a full engine-level comparison.

## Best practices

- **Use meaningful IDs when a natural key exists** — email address, URL slug, external system ID. This avoids an extra lookup.
- **Let Firestore auto-generate when no natural key exists** — the random 20-character string provides good distribution and uniqueness.
- **Keep IDs short** — shorter IDs mean smaller index entries and lower storage costs.
- **Avoid sequential patterns** — `order_1`, `order_2`, etc. cause hotspots. Use UUIDs or random strings if you must generate IDs yourself.
- **Don't encode hierarchy in IDs** — use subcollections instead of IDs like `user_123_order_456`.
