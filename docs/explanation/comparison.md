# Firestore SDK vs NDB vs Cendry

Side-by-side comparison of common use cases across three approaches:

- **Firestore SDK** — `google-cloud-firestore`, the official low-level client
- **NDB** — `google-cloud-ndb`, the legacy App Engine ORM (Datastore mode only)
- **Cendry** — typed ODM for Firestore Native mode

!!! warning "NDB is deprecated for new projects"
    [Cloud NDB](https://github.com/googleapis/python-ndb) only works with **Firestore in Datastore mode** — it does [not support Firestore Native mode](https://github.com/googleapis/python-ndb/issues/140). Google recommends [Firestore Native mode for all new applications](https://cloud.google.com/datastore/docs/firestore-or-datastore). NDB is shown here for developers migrating from App Engine.

---

## Define a model

=== "NDB (deprecated)"

    ```python
    from google.cloud import ndb

    class City(ndb.Model):
        name = ndb.StringProperty()
        state = ndb.StringProperty()
        population = ndb.IntegerProperty()
        mayor = ndb.StructuredProperty(Mayor)  # nested
    ```

    No type annotations, no IDE autocomplete on fields.

=== "Firestore SDK"

    No model layer — you work with raw dicts.

    ```python
    # No model definition — just use dicts everywhere
    city_data = {
        "name": "San Francisco",
        "state": "CA",
        "population": 870000,
    }
    ```

=== "Cendry"

    ```python
    from cendry import Model, Map, Field, field

    class Mayor(Map):
        name: Field[str]
        since: Field[int]

    class City(Model, collection="cities"):
        name: Field[str]
        state: Field[str]
        population: Field[int]
        mayor: Field[Mayor | None] = field(default=None)
    ```

    Type annotations validated at class definition. Full IDE support.

---

## Read a document

=== "NDB (deprecated)"

    ```python
    city = City.get_by_id("SF")
    if city is None:
        raise Exception("Not found")
    print(city.name)
    ```

=== "Firestore SDK"

    ```python
    from google.cloud.firestore import Client

    client = Client()
    doc = client.collection("cities").document("SF").get()
    if not doc.exists:
        raise Exception("Not found")
    data = doc.to_dict()
    name = data["name"]       # no type safety
    population = data["pop"]  # typo? no error at all
    ```

=== "Cendry"

    ```python
    from cendry import Cendry

    with Cendry() as ctx:
        city = ctx.get(City, "SF")  # raises DocumentNotFoundError
        print(city.name)            # typed, IDE autocomplete
        print(city.population)      # typo → immediate error
    ```

---

## Query with filters

=== "NDB (deprecated)"

    ```python
    cities = City.query(
        City.state == "CA",
        City.population > 1_000_000,
    ).order(-City.population).fetch(10)
    ```

=== "Firestore SDK"

    ```python
    from google.cloud.firestore_v1.base_query import FieldFilter

    query = (
        client.collection("cities")
        .where(filter=FieldFilter("state", "==", "CA"))
        .where(filter=FieldFilter("population", ">", 1_000_000))
        .order_by("population", direction="DESCENDING")
        .limit(10)
    )
    for doc in query.stream():
        data = doc.to_dict()
        print(data["name"], data["population"])
    ```

=== "Cendry"

    ```python
    cities = (
        ctx.select(City)
        .filter(City.state == "CA", City.population > 1_000_000)
        .order_by(City.population.desc())
        .limit(10)
        .to_list()
    )
    for city in cities:
        print(city.name, city.population)
    ```

---

## Save a document

=== "NDB (deprecated)"

    ```python
    city = City(name="San Francisco", state="CA", population=870000)
    city.put()
    print(city.key.id())
    ```

=== "Firestore SDK"

    ```python
    client.collection("cities").document("SF").set({
        "name": "San Francisco",
        "state": "CA",
        "population": 870000,
    })
    ```

=== "Cendry"

    ```python
    city = City(name="San Francisco", state="CA", population=870_000)
    ctx.save(city)  # auto-generates ID, validates fields
    print(city.id)  # ID set automatically
    ```

---

## Partial update

=== "NDB (deprecated)"

    ```python
    city = City.get_by_id("SF")
    city.population = 900_000
    city.put()  # overwrites entire entity — no partial update
    ```

    NDB doesn't support partial updates — you must fetch, modify, and re-save the entire entity.

=== "Firestore SDK"

    ```python
    from google.cloud.firestore import Increment

    client.collection("cities").document("SF").update({
        "population": Increment(1000),
        "mayor.name": "Jane",
    })
    ```

=== "Cendry"

    ```python
    from cendry import Increment

    ctx.update(city, {
        "population": Increment(1000),
        "mayor.name": "Jane",
    })
    # or by class + ID:
    ctx.update(City, "SF", {"population": Increment(1000)})
    ```

---

## Delete a document

=== "NDB (deprecated)"

    ```python
    key = ndb.Key("City", "SF")
    key.delete()
    ```

=== "Firestore SDK"

    ```python
    client.collection("cities").document("SF").delete()
    # silent if it doesn't exist — no way to know
    ```

=== "Cendry"

    ```python
    ctx.delete(city)
    ctx.delete(City, "SF")
    ctx.delete(City, "SF", must_exist=True)  # raises if missing
    ```

---

## Batch writes

=== "NDB (deprecated)"

    ```python
    ndb.put_multi([city1, city2, city3])
    ndb.delete_multi([key1, key2])
    ```

=== "Firestore SDK"

    ```python
    batch = client.batch()
    for city_data in cities_data:
        ref = client.collection("cities").document()
        batch.set(ref, city_data)
    batch.commit()
    ```

=== "Cendry"

    ```python
    ctx.save_many(cities)  # one line, max 500, atomic

    # or mix operations:
    with ctx.batch() as batch:
        batch.save(city1)
        batch.update(city2, {"population": 1_000_000})
        batch.delete(city3)
    ```

---

## Transactions

=== "NDB (deprecated)"

    ```python
    @ndb.transactional
    def transfer():
        sf = City.get_by_id("SF")
        la = City.get_by_id("LA")
        sf.population -= 1000
        la.population += 1000
        ndb.put_multi([sf, la])

    transfer()
    ```

=== "Firestore SDK"

    ```python
    from google.cloud.firestore_v1.transaction import transactional

    transaction = client.transaction()

    @transactional
    def transfer(transaction, from_ref, to_ref, amount):
        from_doc = transaction.get(from_ref).to_dict()
        to_doc = transaction.get(to_ref).to_dict()
        transaction.update(from_ref, {
            "population": from_doc["population"] - amount,
        })
        transaction.update(to_ref, {
            "population": to_doc["population"] + amount,
        })

    from_ref = client.collection("cities").document("SF")
    to_ref = client.collection("cities").document("LA")
    transfer(transaction, from_ref, to_ref, 1000)
    ```

=== "Cendry"

    ```python
    def transfer(txn):
        sf = txn.get(City, "SF")
        la = txn.get(City, "LA")
        txn.update(sf, {"population": sf.population - 1000})
        txn.update(la, {"population": la.population + 1000})

    ctx.transaction(transfer)
    ```

---

## Nested data (Maps)

=== "NDB (deprecated)"

    ```python
    class Mayor(ndb.Model):
        name = ndb.StringProperty()

    class City(ndb.Model):
        mayor = ndb.StructuredProperty(Mayor)

    city = City.get_by_id("SF")
    print(city.mayor.name)  # typed but no IDE support
    ```

=== "Firestore SDK"

    ```python
    doc = client.collection("cities").document("SF").get()
    data = doc.to_dict()
    mayor_name = data.get("mayor", {}).get("name")  # nested dict access
    ```

=== "Cendry"

    ```python
    city = ctx.get(City, "SF")
    print(city.mayor.name)  # typed Map, IDE autocomplete
    ```

---

## Optimistic locking

=== "NDB (deprecated)"

    NDB doesn't have built-in optimistic locking. You must use transactions for conflict resolution.

=== "Firestore SDK"

    ```python
    from google.cloud.firestore_v1._helpers import LastUpdateOption

    doc = client.collection("cities").document("SF").get()
    client.collection("cities").document("SF").update(
        {"population": 900_000},
        option=LastUpdateOption(doc.update_time),
    )
    ```

=== "Cendry"

    ```python
    city = ctx.get(City, "SF")
    ctx.update(city, {"population": 900_000}, if_unchanged=True)
    ```

---

## Summary

| Aspect | NDB (deprecated) | Firestore SDK | Cendry |
|--------|------------------|--------------|--------|
| **Database** | Datastore mode only | Native mode | Native mode |
| **Model layer** | `ndb.Model` — no type annotations | None — raw dicts | `Model` + `Field[T]` — typed |
| **Data access** | `instance.field` — untyped | `dict["field"]` — untyped | `instance.field` — typed |
| **Filters** | `City.state == "CA"` | `FieldFilter("state", "==", "CA")` | `City.state == "CA"` |
| **Partial update** | Not supported | `doc.update({...})` | `ctx.update(instance, {...})` |
| **Nested data** | `StructuredProperty` | Nested dicts | `Map` class — typed |
| **Optimistic lock** | Not supported | `LastUpdateOption(...)` | `if_unchanged=True` |
| **Async** | Not supported | `AsyncClient` | `AsyncCendry` |
| **IDE support** | Minimal | None | Full autocomplete + type checking |
| **Status** | Legacy — Datastore only | Active — low-level | Active — typed ODM |
