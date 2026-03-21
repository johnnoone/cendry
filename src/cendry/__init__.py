"""Cendry — A Firestore ODM for Python."""

from google.cloud.firestore import (
    DELETE_FIELD,
    SERVER_TIMESTAMP,
    ArrayRemove,
    ArrayUnion,
    Increment,
    Maximum,
    Minimum,
)

from .context import AsyncCendry, Cendry
from .exceptions import CendryError, DocumentAlreadyExistsError, DocumentNotFoundError
from .filters import And, FieldFilter, Or
from .model import Field, FieldDescriptor, Map, Model, field
from .query import Asc, AsyncQuery, Desc, Query
from .serialize import from_dict, to_dict
from .types import BaseTypeHandler, TypeHandler, TypeRegistry, register_type

__all__ = [
    "And",
    "ArrayRemove",
    "ArrayUnion",
    "Asc",
    "AsyncCendry",
    "AsyncQuery",
    "BaseTypeHandler",
    "Cendry",
    "CendryError",
    "DELETE_FIELD",
    "Desc",
    "DocumentAlreadyExistsError",
    "DocumentNotFoundError",
    "Field",
    "FieldDescriptor",
    "FieldFilter",
    "Increment",
    "Map",
    "Maximum",
    "Minimum",
    "Model",
    "Or",
    "Query",
    "SERVER_TIMESTAMP",
    "TypeHandler",
    "TypeRegistry",
    "field",
    "from_dict",
    "register_type",
    "to_dict",
]
