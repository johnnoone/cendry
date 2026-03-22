# Context Reference

::: cendry.context.Cendry
    options:
      members:
        - get
        - find
        - get_many
        - select
        - select_group
        - save
        - create
        - update
        - delete
        - refresh
        - batch
        - save_many
        - delete_many
        - transaction

---

::: cendry.context.AsyncCendry
    options:
      members:
        - get
        - find
        - get_many
        - select
        - select_group
        - save
        - create
        - update
        - delete
        - refresh
        - batch
        - save_many
        - delete_many
        - transaction

---

::: cendry.batch.Batch
    options:
      members:
        - save
        - create
        - update
        - delete

---

::: cendry.batch.AsyncBatch
    options:
      members:
        - save
        - create
        - update
        - delete

---

::: cendry.transaction.Txn
    options:
      members:
        - get
        - find
        - save
        - create
        - update
        - delete

---

::: cendry.transaction.AsyncTxn
    options:
      members:
        - get
        - find
        - save
        - create
        - update
        - delete
