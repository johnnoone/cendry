# How-To Guides

Practical recipes for specific tasks. Each guide is self-contained — jump to what you need.

---

**[Define Models](models.md)**
:   Models, Maps, fields, defaults, enums, inheritance.

**[Work with Document IDs](document-ids.md)**
:   ID types, constraints, auto-generation, manual IDs.

**[Auto-Timestamps](auto-timestamps.md)**
:   Automatically set created/updated timestamps on save.

**[Write, Update, and Delete](writing.md)**
:   Save, create, update, delete, refresh, optimistic locking.

**[Batch Writes and Transactions](batch-and-transactions.md)**
:   Atomic multi-document writes, save_many/delete_many, transactions.

**[Filter and Query](filtering.md)**
:   Operators, composition, chainable queries, operator reference table.

**[Use Aliases](aliases.md)**
:   When Firestore field names differ from Python attribute names.

**[Serialize Data](serialization.md)**
:   `from_dict`, `to_dict`, testing without a Firestore connection.

**[Extend Type Validation](type-validation.md)**
:   Register custom types, type handlers, supported types reference.

**[Use Async](async.md)**
:   `AsyncCendry`, `AsyncQuery`, anyio, async iteration.

**[Test with Emulator](testing.md)**
:   Integration tests with Firestore emulator via testcontainers.

**[Migrate from Datastore to Native](migrate-datastore-to-native.md)**
:   Step-by-step migration from Firestore Datastore mode to Native mode.
