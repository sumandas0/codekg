"""
Factory module for graph storage implementations.
"""
from typing import Any

from .base import BaseGraphStorage
from .memgraph import MemgraphStorage
from .falkordb import FalkorDBStorage
from .neo4j import Neo4jStorage
from .kuzudb import KuzuDBStorage


def get_storage_implementation(storage_type: str = "memgraph", **kwargs: Any) -> BaseGraphStorage:
    """
    Factory function to get the appropriate storage implementation.
    
    Args:
        storage_type: Type of storage ('memgraph', 'falkordb', 'neo4j', 'kuzudb')
        **kwargs: Additional arguments to pass to the storage constructor
        
    Returns:
        An instance of the appropriate storage implementation
    """
    storage_mapping = {
        "memgraph": MemgraphStorage,
        "falkordb": FalkorDBStorage,
        "neo4j": Neo4jStorage,
        "kuzudb": KuzuDBStorage
    }
    
    if storage_type not in storage_mapping:
        raise ValueError(f"Unsupported storage type: {storage_type}. Supported types: {list(storage_mapping.keys())}")
    
    storage_class = storage_mapping[storage_type]
    return storage_class(**kwargs) 