def test_public_api_exports():
    import cendry

    expected = [
        "And",
        "Asc",
        "AsyncCendry",
        "Cendry",
        "CendryError",
        "Desc",
        "DocumentNotFoundError",
        "Field",
        "FieldFilter",
        "Map",
        "Model",
        "Or",
        "field",
    ]
    for name in expected:
        assert hasattr(cendry, name), f"Missing export: {name}"
    assert set(expected) == set(cendry.__all__)
