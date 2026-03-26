# Auto-Timestamps

Automatically track creation and modification times on your models, ported from Google NDB's `auto_now` and `auto_now_add` behavior.

## Quick Start

```python
import datetime
from cendry import Model, Field, field

class Article(Model, collection="articles"):
    title: Field[str]
    created_at: Field[datetime.datetime | None] = field(auto_now_add=True)
    updated_at: Field[datetime.datetime | None] = field(auto_now=True)
```

## How It Works

| Parameter | Behavior | When |
|---|---|---|
| `auto_now_add=True` | Sets field to current UTC time **only if the value is `None`** | `save()`, `create()` |
| `auto_now=True` | **Always** overwrites field with current UTC time | `save()`, `create()` |

Both work on `save()`, `create()`, and their batch/transaction equivalents. They do **not** apply to `update()`.

## Supported Types

```python
class Event(Model, collection="events"):
    # datetime — datetime.datetime.now(tz=UTC)
    timestamp: Field[datetime.datetime | None] = field(auto_now=True)

    # date — datetime.datetime.now(tz=UTC).date()
    day: Field[datetime.date | None] = field(auto_now=True)

    # time — datetime.datetime.now(tz=UTC).time() (naive, no tzinfo)
    at_time: Field[datetime.time | None] = field(auto_now=True)
```

!!! info "Built-in Firestore storage"

    `datetime.date` and `datetime.time` have built-in handlers — Cendry automatically converts them to Firestore-compatible `datetime.datetime` values (date at midnight UTC, time on 1970-01-01 UTC). No manual `register_type()` needed. See [Built-in handlers](type-validation.md#built-in-handlers).

## Rules

- `auto_now` and `auto_now_add` are **mutually exclusive** on the same field
- Cannot combine with explicit `default` or `default_factory`
- Fields get an implicit `default=None` — you don't need to set it
- Only works on `datetime`, `date`, and `time` types (or their `| None` variants)
- You can manually set values — `auto_now_add` respects them, `auto_now` overwrites them

!!! tip "NDB Migration"
    If you're migrating from NDB, `auto_now` and `auto_now_add` behave identically to NDB's `DateTimeProperty(auto_now=True)` and `DateTimeProperty(auto_now_add=True)`.
