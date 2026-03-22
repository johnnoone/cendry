# What is Firestore?

[Cloud Firestore](https://firebase.google.com/docs/firestore) is a NoSQL document database from Google, part of the Firebase and Google Cloud platforms. It stores data as **documents** organized into **collections**.

Key characteristics:

- **Document-oriented** — each document is a set of key-value pairs, similar to a JSON object
- **Real-time** — supports real-time listeners for live data updates
- **Serverless** — no infrastructure to manage, scales automatically
- **Strong consistency** — single-document reads and writes are strongly consistent
- **Multi-platform** — SDKs for Web, iOS, Android, Python, Go, Java, .NET, and more

## Core concepts

| Concept | Description |
|---------|-------------|
| **Document** | A record with fields and values, identified by a unique ID within a collection |
| **Collection** | A container for documents (like a table in SQL) |
| **Subcollection** | A collection nested under a document (e.g., a city's neighborhoods) |
| **Document reference** | A pointer to a document's location in the database |
| **Query** | A request to retrieve documents matching certain conditions |

## How Cendry maps to Firestore

| Firestore concept | Cendry equivalent |
|-------------------|-------------------|
| Document | `Model` instance |
| Collection | `Model` class with `collection="..."` |
| Subcollection | `parent=` parameter on queries and writes |
| Nested map | `Map` class |
| Document ID | `instance.id` |
| Document fields | `Field[T]` annotations |
| FieldFilter | `City.state == "CA"` (Python operators) |
| WriteBatch | `Batch` / `ctx.batch()` |
| Transaction | `Txn` / `ctx.transaction()` |

## Official documentation

- **[Firestore documentation](https://firebase.google.com/docs/firestore)** — getting started, data model, security rules
- **[Python SDK reference](https://cloud.google.com/python/docs/reference/firestore/latest)** — the `google-cloud-firestore` library that Cendry wraps
- **[Data model](https://firebase.google.com/docs/firestore/data-model)** — documents, collections, subcollections
- **[Query data](https://firebase.google.com/docs/firestore/query-data/get-data)** — reading and querying documents
- **[Add and manage data](https://firebase.google.com/docs/firestore/manage-data/add-data)** — writing, updating, deleting
- **[Transactions](https://firebase.google.com/docs/firestore/manage-data/transactions)** — atomic read-write operations
- **[Batch writes](https://firebase.google.com/docs/firestore/manage-data/transactions#batched-writes)** — atomic multi-document writes
- **[Firestore emulator](https://firebase.google.com/docs/emulator-suite/connect_firestore)** — local development without a Google Cloud account
