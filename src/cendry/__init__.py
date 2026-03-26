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

from .backend import AsyncBackend, Backend
from .backends.firestore import FirestoreAsyncBackend, FirestoreBackend
from .backends.types import DocResult, WriteResult
from .batch import AsyncBatch, Batch
from .context import AsyncCendry, Cendry
from .exceptions import CendryError, DocumentAlreadyExistsError, DocumentNotFoundError
from .filters import And, FieldFilter, Or
from .metadata import DocumentMetadata, get_metadata
from .model import Field, FieldDescriptor, Map, Model, field
from .query import Asc, AsyncProjectedQuery, AsyncQuery, Desc, ProjectedQuery, Query
from .serialize import from_dict, to_dict
from .transaction import AsyncTxn, Txn
from .types import BaseTypeHandler, FirestoreValue, TypeHandler, TypeRegistry, register_type

__all__ = [
    "DELETE_FIELD",
    "SERVER_TIMESTAMP",
    "And",
    "ArrayRemove",
    "ArrayUnion",
    "Asc",
    "AsyncBackend",
    "AsyncBatch",
    "AsyncCendry",
    "AsyncProjectedQuery",
    "AsyncQuery",
    "AsyncTxn",
    "Backend",
    "BaseTypeHandler",
    "Batch",
    "Cendry",
    "CendryError",
    "Desc",
    "DocResult",
    "DocumentAlreadyExistsError",
    "DocumentMetadata",
    "DocumentNotFoundError",
    "Field",
    "FieldDescriptor",
    "FieldFilter",
    "FirestoreAsyncBackend",
    "FirestoreBackend",
    "FirestoreValue",
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
    "WriteResult",
    "field",
    "from_dict",
    "get_metadata",
    "register_type",
    "to_dict",
]
