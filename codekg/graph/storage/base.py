"""
Base storage interface for graph databases in CodeKG.

This module provides the base protocol and abstract class for graph database backends.
"""
from typing import Dict, List, Optional, Any, Protocol, runtime_checkable
import logging
import abc


@runtime_checkable
class GraphStorageInterface(Protocol):
    """Protocol defining the interface for graph database storage."""
    
    def connect(self) -> bool:
        """
        Connect to the database.
        
        Returns:
            True if connection successful, False otherwise
        """
        ...
    
    def close(self) -> None:
        """Close the database connection."""
        ...
    
    def clear(self) -> None:
        """Clear all data from the database."""
        ...
    
    def create_indexes(self) -> None:
        """Create necessary indexes for the database."""
        ...
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a query against the database.
        
        Args:
            query: The query string (Cypher or equivalent)
            params: Optional parameters for the query
            
        Returns:
            List of result records as dictionaries
        """
        ...
    
    def save_entity(self, entity_id: str, labels: List[str], properties: Dict[str, Any]) -> None:
        """
        Save an entity to the database.
        
        Args:
            entity_id: The unique ID of the entity
            labels: List of labels for the entity
            properties: Dictionary of entity properties
        """
        ...
    
    def save_relationship(self, source_id: str, target_id: str, rel_type: str, properties: Dict[str, Any]) -> None:
        """
        Save a relationship to the database.
        
        Args:
            source_id: ID of the source entity
            target_id: ID of the target entity
            rel_type: Type of the relationship
            properties: Dictionary of relationship properties
        """
        ...
    
    def count_nodes(self, label: Optional[str] = None) -> int:
        """
        Count nodes in the database, optionally filtered by label.
        
        Args:
            label: Optional node label to filter by
            
        Returns:
            Count of matching nodes
        """
        ...
    
    def count_relationships(self, type_: Optional[str] = None) -> int:
        """
        Count relationships in the database, optionally filtered by type.
        
        Args:
            type_: Optional relationship type to filter by
            
        Returns:
            Count of matching relationships
        """
        ...
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the database.
        
        Returns:
            Dictionary with statistics
        """
        ...
    
    def export_to_csv(self, export_dir: str) -> None:
        """
        Export the database to CSV files.
        
        Args:
            export_dir: Directory to export CSV files to
        """
        ...
    
    def import_from_csv(self, import_dir: str) -> None:
        """
        Import the database from CSV files.
        
        Args:
            import_dir: Directory to import CSV files from
        """
        ...


class BaseGraphStorage(abc.ABC):
    """Abstract base class for graph database storage implementations."""
    
    def __init__(self, host: str = "localhost", port: int = 7687,
                username: Optional[str] = None, password: Optional[str] = None,
                **kwargs: Any):
        """
        Initialize the storage.
        
        Args:
            host: Database server hostname
            port: Database server port
            username: Optional username for authentication
            password: Optional password for authentication
            **kwargs: Additional implementation-specific arguments
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.is_connected = False
        
    @abc.abstractmethod
    def connect(self) -> bool:
        """Connect to the database."""
        pass
    
    @abc.abstractmethod
    def close(self) -> None:
        """Close the database connection."""
        pass
    
    @abc.abstractmethod
    def clear(self) -> None:
        """Clear all data from the database."""
        pass
    
    @abc.abstractmethod
    def create_indexes(self) -> None:
        """Create necessary indexes for the database."""
        pass
    
    @abc.abstractmethod
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a query against the database."""
        pass
    
    @abc.abstractmethod
    def save_entity(self, entity_id: str, labels: List[str], properties: Dict[str, Any]) -> None:
        """Save an entity to the database."""
        pass
    
    @abc.abstractmethod
    def save_relationship(self, source_id: str, target_id: str, rel_type: str, properties: Dict[str, Any]) -> None:
        """Save a relationship to the database."""
        pass
    
    @abc.abstractmethod
    def count_nodes(self, label: Optional[str] = None) -> int:
        """Count nodes in the database."""
        pass
    
    @abc.abstractmethod
    def count_relationships(self, type_: Optional[str] = None) -> int:
        """Count relationships in the database."""
        pass
    
    @abc.abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the database."""
        pass
    
    @abc.abstractmethod
    def export_to_csv(self, export_dir: str) -> None:
        """Export the database to CSV files."""
        pass
    
    @abc.abstractmethod
    def import_from_csv(self, import_dir: str) -> None:
        """Import the database from CSV files."""
        pass 