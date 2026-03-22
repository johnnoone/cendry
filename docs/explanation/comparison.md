# Firestore SDK vs Cendry

Side-by-side comparison of common use cases. Left is raw `google-cloud-firestore`, right is Cendry.

---

## Read a document

=== "Firestore SDK"

    ```python
    from google.cloud.firestore import Client

    client = Client()
    doc = client.collection("cities").document("SF").get()
    if not doc.exists:
        raise Exception("Not found")
    data = doc.to_dict()
    name = data["name"]       # no type safety
    population = data["pop"]  # typo? no error
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

| Aspect | Firestore SDK | Cendry |
|--------|--------------|--------|
| **Data access** | `dict["field"]` — untyped | `instance.field` — typed |
| **Filters** | `FieldFilter("field", "op", value)` | `City.field == value` |
| **Validation** | None — write anything | Fields validated at class definition |
| **Nested data** | `dict.get("a", {}).get("b")` | `instance.a.b` |
| **Serialization** | Manual dict construction | Automatic via `to_dict`/`from_dict` |
| **ID management** | Manual `document()` calls | Auto-generated, set on instance |
| **Error handling** | Raw Google exceptions | `DocumentNotFoundError`, `DocumentAlreadyExistsError` |
| **Optimistic lock** | `LastUpdateOption(doc.update_time)` | `if_unchanged=True` |
| **IDE support** | None | Full autocomplete, type checking |
