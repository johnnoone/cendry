# Use TTL Policies

Firestore can **automatically delete documents** after a timestamp you set. TTL (time-to-live) policies are configured server-side — Cendry's role is setting the expiry field on your models.

---

## Define a TTL field

Add a `datetime` field to your model. This is the field Firestore will check for expiry:

```python
from datetime import datetime
from cendry import Model, Field

class Session(Model, collection="sessions"):
    user_id: Field[str]
    token: Field[str]
    expires_at: Field[datetime]
```

There's nothing special about the field — it's a regular `Field[datetime]`.

## Set expiry on creation

Set `expires_at` to the desired expiry time when creating a document:

```python
from datetime import UTC, datetime, timedelta

session = Session(
    user_id="user_123",
    token="abc-secret-token",
    expires_at=datetime.now(UTC) + timedelta(hours=24),
)
ctx.save(session)
```

Firestore will delete the document after `expires_at` passes.

## Configure the TTL policy

The TTL policy is configured **server-side**, not through the client SDK. You only need to do this once per collection.

=== "Console"

    1. Go to [Cloud Console → Firestore](https://console.cloud.google.com/firestore)
    2. Click **TTL** in the left navigation
    3. Click **Create policy**
    4. Enter the collection group name (e.g., `sessions`)
    5. Enter the field path (e.g., `expires_at`)
    6. Click **Create**

=== "gcloud CLI"

    ```bash
    gcloud firestore fields ttls update expires_at \
        --collection-group=sessions \
        --enable-ttl
    ```

!!! warning "Behavior notes"
    - **Deletion is eventual** — documents are typically deleted within **24 hours** of expiry, not instantly.
    - **Expired docs still appear in queries** — until Firestore actually deletes them, they show up in reads and queries.
    - **Subcollections are NOT deleted** — only the document itself is removed.
    - **Deletes count toward billing** — each TTL deletion is billed as a document delete.
    - **One TTL field per collection group** — you can't have multiple TTL fields on the same collection.

## Common patterns

### Session tokens

Expire sessions after 24 hours:

```python
class Session(Model, collection="sessions"):
    user_id: Field[str]
    token: Field[str]
    expires_at: Field[datetime]

session = Session(
    user_id="user_123",
    token="abc-secret-token",
    expires_at=datetime.now(UTC) + timedelta(hours=24),
)
ctx.save(session)
```

### Audit logs

Keep audit logs for 90 days:

```python
class AuditLog(Model, collection="audit_logs"):
    action: Field[str]
    actor: Field[str]
    details: Field[str]
    expires_at: Field[datetime]

log = AuditLog(
    action="user.login",
    actor="user_123",
    details="Login from 192.168.1.1",
    expires_at=datetime.now(UTC) + timedelta(days=90),
)
ctx.save(log)
```

### Temporary uploads

Clean up temporary file metadata after 1 hour:

```python
class TempUpload(Model, collection="temp_uploads"):
    filename: Field[str]
    storage_path: Field[str]
    expires_at: Field[datetime]

upload = TempUpload(
    filename="photo.jpg",
    storage_path="gs://bucket/tmp/photo.jpg",
    expires_at=datetime.now(UTC) + timedelta(hours=1),
)
ctx.save(upload)
```

!!! tip "Combine with `auto_now_add`"
    If you want a `created_at` field alongside your TTL field, use [auto-timestamps](auto-timestamps.md):

    ```python
    from cendry import field

    class TempUpload(Model, collection="temp_uploads"):
        filename: Field[str]
        created_at: Field[datetime | None] = field(auto_now_add=True)
        expires_at: Field[datetime]
    ```

## Further reading

- [Manage data retention with TTL policies](https://firebase.google.com/docs/firestore/ttl) — Firebase documentation
- [TTL policies (Google Cloud)](https://cloud.google.com/firestore/native/docs/ttl) — Native mode documentation
