def test_public_api_exports():
    import cendry

    expected = [
        "And",
        "Asc",
        "AsyncCendry",
        "AsyncQuery",
        "BaseTypeHandler",
        "Cendry",
        "CendryError",
        "Desc",
        "DocumentNotFoundError",
        "Field",
        "FieldDescriptor",
        "FieldFilter",
        "Map",
        "Model",
        "Or",
        "Query",
        "TypeHandler",
        "TypeRegistry",
        "field",
        "from_dict",
        "register_type",
        "to_dict",
    ]
    for name in expected:
        assert hasattr(cendry, name), f"Missing export: {name}"
    assert set(expected) == set(cendry.__all__)


def test_py_typed_marker_exists():
    """PEP 561: package must include py.typed marker for type checkers."""
    from pathlib import Path

    import cendry

    package_dir = Path(cendry.__file__).parent
    py_typed = package_dir / "py.typed"
    assert py_typed.exists(), f"py.typed marker not found at {py_typed}"
