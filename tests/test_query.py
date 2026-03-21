from cendry import Asc, Desc, Field, Model


def test_asc_with_string():
    a = Asc("population")
    assert a.field == "population"
    assert a.direction == "ASCENDING"


def test_desc_with_string():
    d = Desc("population")
    assert d.field == "population"
    assert d.direction == "DESCENDING"


def test_asc_with_field_descriptor():
    class City(Model, collection="cities"):
        population: Field[int]

    a = Asc(City.population)
    assert isinstance(a.field, str)
    assert a.field == "population"
    assert a.direction == "ASCENDING"


def test_desc_with_field_descriptor():
    class City(Model, collection="cities"):
        population: Field[int]

    d = Desc(City.population)
    assert isinstance(d.field, str)
    assert d.field == "population"
    assert d.direction == "DESCENDING"
