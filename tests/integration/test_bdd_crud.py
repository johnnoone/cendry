"""BDD integration tests for CRUD operations."""

from pytest_bdd import given, parsers, scenario, then, when

from cendry import Cendry, DocumentAlreadyExistsError, Field, Model
from cendry.metadata import get_metadata

FEATURES = "features"


class City(Model, collection="bdd_cities"):
    name: Field[str]
    population: Field[int]


@scenario(f"{FEATURES}/crud.feature", "Save and retrieve a document")
def test_save_and_retrieve():
    pass


@scenario(f"{FEATURES}/crud.feature", "Save overwrites an existing document")
def test_save_overwrites():
    pass


@scenario(f"{FEATURES}/crud.feature", "Create a duplicate raises DocumentAlreadyExistsError")
def test_create_duplicate():
    pass


@scenario(f"{FEATURES}/crud.feature", "Partial update changes only specified fields")
def test_partial_update():
    pass


@scenario(f"{FEATURES}/crud.feature", "Delete removes the document")
def test_delete():
    pass


@scenario(f"{FEATURES}/crud.feature", "Refresh re-fetches from Firestore")
def test_refresh():
    pass


@scenario(f"{FEATURES}/crud.feature", "Metadata is populated on read")
def test_metadata():
    pass


# --- Given ---


@given(
    "a Cendry context connected to the emulator",
    target_fixture="ctx_state",
)
def cendry_context(firestore_client, clean_collection):
    clean_collection("bdd_cities")
    return {"ctx": Cendry(client=firestore_client), "instance": None, "result": None}


@given(
    parsers.parse('a saved City "{doc_id}" with population {pop:d}'),
    target_fixture="ctx_state",
)
def saved_city(firestore_client, clean_collection, doc_id: str, pop: int):
    clean_collection("bdd_cities")
    ctx = Cendry(client=firestore_client)
    instance = City(name="San Francisco", population=pop, id=doc_id)
    ctx.save(instance)
    return {"ctx": ctx, "instance": instance, "result": None, "client": firestore_client}


@given(
    parsers.parse("2 saved cities"),
    target_fixture="ctx_state",
)
def two_saved_cities(firestore_client, clean_collection):
    clean_collection("bdd_cities")
    ctx = Cendry(client=firestore_client)
    c1 = City(name="A", population=1, id="a")
    c2 = City(name="B", population=2, id="b")
    ctx.save_many([c1, c2])
    return {"ctx": ctx, "instances": [c1, c2], "result": None}


# --- When ---


@when(
    parsers.parse('I save a City with name "{name}" and population {pop:d}'),
    target_fixture="ctx_state",
)
def save_city(ctx_state, name: str, pop: int):
    ctx = ctx_state["ctx"]
    instance = City(name=name, population=pop)
    ctx.save(instance)
    ctx_state["instance"] = instance
    return ctx_state


@when(
    parsers.parse("I update its population to {pop:d} and save again"),
    target_fixture="ctx_state",
)
def update_and_save(ctx_state, pop: int):
    ctx_state["instance"].population = pop
    ctx_state["ctx"].save(ctx_state["instance"])
    return ctx_state


@when(
    parsers.parse('I create another City with ID "{doc_id}"'),
    target_fixture="ctx_state",
)
def create_duplicate(ctx_state, doc_id: str):
    try:
        ctx_state["ctx"].create(City(name="Dup", population=0, id=doc_id))
    except DocumentAlreadyExistsError as e:
        ctx_state["result"] = e
    return ctx_state


@when(
    parsers.parse("I update population to {pop:d}"),
    target_fixture="ctx_state",
)
def update_population(ctx_state, pop: int):
    ctx_state["ctx"].update(ctx_state["instance"], {"population": pop})
    return ctx_state


@when("I delete it", target_fixture="ctx_state")
def delete_it(ctx_state):
    ctx_state["ctx"].delete(ctx_state["instance"])
    return ctx_state


@when(
    parsers.parse("another client changes population to {pop:d}"),
    target_fixture="ctx_state",
)
def external_update(ctx_state, pop: int):
    ctx_state["client"].collection("bdd_cities").document(ctx_state["instance"].id).update(
        {"population": pop}
    )
    return ctx_state


@when("I refresh the instance", target_fixture="ctx_state")
def refresh(ctx_state):
    ctx_state["ctx"].refresh(ctx_state["instance"])
    return ctx_state


@when("I read it with ctx.get", target_fixture="ctx_state")
def read_with_get(ctx_state):
    ctx_state["fetched"] = ctx_state["ctx"].get(City, ctx_state["instance"].id)
    return ctx_state


# --- Then ---


@then("the City has an auto-generated ID")
def check_auto_id(ctx_state):
    assert ctx_state["instance"].id is not None


@then("I can retrieve it by ID with matching fields")
def check_retrieve(ctx_state):
    fetched = ctx_state["ctx"].get(City, ctx_state["instance"].id)
    assert fetched.name == "San Francisco"
    assert fetched.population == 870_000


@then(parsers.parse('retrieving "{doc_id}" shows population {pop:d}'))
def check_population(ctx_state, doc_id: str, pop: int):
    fetched = ctx_state["ctx"].get(City, doc_id)
    assert fetched.population == pop


@then("a DocumentAlreadyExistsError is raised")
def check_already_exists(ctx_state):
    assert isinstance(ctx_state["result"], DocumentAlreadyExistsError)


@then(parsers.parse('the name is still "{name}"'))
def check_name(ctx_state, name: str):
    fetched = ctx_state["ctx"].get(City, ctx_state["instance"].id)
    assert fetched.name == name


@then(parsers.parse('finding "{doc_id}" returns None'))
def check_find_none(ctx_state, doc_id: str):
    assert ctx_state["ctx"].find(City, doc_id) is None


@then(parsers.parse("the instance population is {pop:d}"))
def check_instance_population(ctx_state, pop: int):
    assert ctx_state["instance"].population == pop


@then("get_metadata returns update_time and create_time")
def check_metadata(ctx_state):
    meta = get_metadata(ctx_state["fetched"])
    assert meta.update_time is not None
    assert meta.create_time is not None
