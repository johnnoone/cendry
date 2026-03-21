from cendry.model import FieldDescriptor


class _Order:
    """Base class for ordering directives."""

    direction: str

    def __init__(self, field: str | FieldDescriptor) -> None:
        if isinstance(field, FieldDescriptor):
            self.field = field.field_name
        else:
            self.field = field


class Asc(_Order):
    """Ascending order."""

    direction = "ASCENDING"


class Desc(_Order):
    """Descending order."""

    direction = "DESCENDING"
