"""
Storage interface for graph databases in CodeKG.

This module provides a common interface for different graph database backends.
"""
# This file now re-exports the components from the storage module
# for backward compatibility
from .storage import (
    GraphStorageInterface,
    BaseGraphStorage,
    MemgraphStorage,
    FalkorDBStorage,
    Neo4jStorage,
    KuzuDBStorage,
    get_storage_implementation
)

__all__ = [
    "GraphStorageInterface",
    "BaseGraphStorage",
    "MemgraphStorage",
    "FalkorDBStorage",
    "Neo4jStorage",
    "KuzuDBStorage",
    "get_storage_implementation",
] 