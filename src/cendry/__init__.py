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

from .batch import AsyncBatch, Batch
from .context import AsyncCendry, Cendry
from .exceptions import CendryError, DocumentAlreadyExistsError, DocumentNotFoundError
from .filters import And, FieldFilter, Or
from .metadata import DocumentMetadata, get_metadata
from .model import Field, FieldDescriptor, Map, Model, field
from .query import Asc, AsyncProjectedQuery, AsyncQuery, Desc, ProjectedQuery, Query
from .serialize import from_dict, to_dict
from .transaction import AsyncTxn, Txn
from .types import BaseTypeHandler, TypeHandler, TypeRegistry, register_type

__all__ = [
    "DELETE_FIELD",
    "SERVER_TIMESTAMP",
    "And",
    "ArrayRemove",
    "ArrayUnion",
    "Asc",
    "AsyncBatch",
    "AsyncCendry",
    "AsyncProjectedQuery",
    "AsyncQuery",
    "AsyncTxn",
    "BaseTypeHandler",
    "Batch",
    "Cendry",
    "CendryError",
    "Desc",
    "DocumentAlreadyExistsError",
    "DocumentMetadata",
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
    "ProjectedQuery",
    "Query",
    "Txn",
    "TypeHandler",
    "TypeRegistry",
    "field",
    "from_dict",
    "get_metadata",
    "register_type",
    "to_dict",
]
