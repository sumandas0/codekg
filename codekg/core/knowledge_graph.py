"""
Main CodeKnowledgeGraph class for managing entities and relationships.
"""
from typing import Dict, List, Optional, Set, Any, Type, Union, Tuple
import uuid
import logging
from collections import defaultdict

from ..graph.storage_interface import BaseGraphStorage, get_storage_implementation

from .entities import CodeResource
from .relationships import Relationship


class CodeKnowledgeGraph:
    """
    The central class for managing the Code Knowledge Graph.
    Handles entity and relationship management and database interactions.
    """
    
    def __init__(self, storage_type: str = "memgraph", storage_config: Optional[Dict[str, Any]] = None):
        """
        Initialize a new Code Knowledge Graph.
        
        Args:
            storage_type: Type of storage backend ('memgraph', 'falkordb', 'neo4j')
            storage_config: Configuration for the storage backend
        """
        self.entities: Dict[str, CodeResource] = {}
        self.relationships: List[Relationship] = []
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize storage
        if storage_config is None:
            storage_config = {}
        
        self.storage = get_storage_implementation(storage_type, **storage_config)
        self.logger.info(f"Initialized graph with {storage_type} storage backend")
        
    def add_entity(self, entity: CodeResource) -> str:
        """
        Add an entity to the graph.
        
        Args:
            entity: The entity to add
            
        Returns:
            The ID of the added entity
        """
        if entity.id in self.entities:
            self.logger.warning(f"Entity with ID {entity.id} already exists. Updating.")
        
        self.entities[entity.id] = entity
        return entity.id
        
    def add_relationship(self, relationship: Relationship) -> None:
        """
        Add a relationship to the graph.
        
        Args:
            relationship: The relationship to add
        """
        if relationship.source not in self.entities:
            raise ValueError(f"Source entity {relationship.source} not found")
        
        if relationship.target not in self.entities:
            raise ValueError(f"Target entity {relationship.target} not found")
        
        self.relationships.append(relationship)
        
    def get_entity(self, entity_id: str) -> Optional[CodeResource]:
        """
        Get an entity by ID.
        
        Args:
            entity_id: The ID of the entity
            
        Returns:
            The entity if found, None otherwise
        """
        return self.entities.get(entity_id)
    
    def get_relationships(self, source_id: Optional[str] = None, 
                         target_id: Optional[str] = None,
                         rel_type: Optional[str] = None) -> List[Relationship]:
        """
        Get relationships matching the given criteria.
        
        Args:
            source_id: Filter by source entity ID
            target_id: Filter by target entity ID
            rel_type: Filter by relationship type
            
        Returns:
            List of matching relationships
        """
        result = []
        for rel in self.relationships:
            if source_id and rel.source != source_id:
                continue
            if target_id and rel.target != target_id:
                continue
            if rel_type and rel.type != rel_type:
                continue
            result.append(rel)
        return result
    
    def save_to_db(self) -> None:
        """Save the entire graph to the database."""
        try:
            # Connect to the storage backend
            if not self.storage.is_connected:
                self.storage.connect()
            
            # Clear existing data (use with caution)
            self.storage.clear()
            
            # Create indexes for better performance
            self.storage.create_indexes()
            
            # Save entities
            for entity_id, entity in self.entities.items():
                # Convert entity to dict and remove special Pydantic fields
                entity_dict = entity.dict()
                entity_dict.pop("id", None)  # We'll use this as the node ID
                
                # Create entity in database
                labels = [entity.__class__.__name__, "CodeResource"]
                self.storage.save_entity(entity_id, labels, entity_dict)
            
            # Save relationships
            for rel in self.relationships:
                rel_dict = rel.dict()
                source_id = rel_dict.pop("source")
                target_id = rel_dict.pop("target")
                rel_type = rel_dict.pop("type")
                
                # Create relationship in database
                self.storage.save_relationship(source_id, target_id, rel_type, rel_dict)
                
            self.logger.info("Graph saved to database successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save graph to database: {e}")
            raise
    
    def load_from_db(self) -> None:
        """Load the graph from the database."""
        try:
            # Connect to the storage backend
            if not self.storage.is_connected:
                self.storage.connect()
            
            self.entities.clear()
            self.relationships.clear()
            
            # Load entities
            query = "MATCH (n:CodeResource) RETURN n"
            results = self.storage.execute_query(query)
            
            for record in results:
                node = record["n"]
                # We'd need to map the node properties to the appropriate entity class
                # This is a simplified version
                entity_id = node.properties.get("id")
                if entity_id:
                    self.entities[entity_id] = node.properties
            
            # Load relationships
            query = "MATCH (source:CodeResource)-[r]->(target:CodeResource) RETURN source.id as source_id, r, target.id as target_id"
            results = self.storage.execute_query(query)
            
            for record in results:
                source_id = record["source_id"]
                target_id = record["target_id"]
                rel = record["r"]
                
                if source_id and target_id:
                    relationship = Relationship(
                        source=source_id,
                        target=target_id,
                        type=rel.type,
                        **rel.properties
                    )
                    self.relationships.append(relationship)
                
            self.logger.info("Graph loaded from database successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load graph from database: {e}")
            raise
    
    def query(self, cypher_query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query against the database.
        
        Args:
            cypher_query: The Cypher query to execute
            params: Optional parameters for the query
            
        Returns:
            List of results
        """
        if not self.storage.is_connected:
            self.storage.connect()
            
        if params is None:
            params = {}
            
        return self.storage.execute_query(cypher_query, params)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the graph."""
        # If connected to database, get stats from there
        if self.storage.is_connected:
            try:
                return self.storage.get_statistics()
            except Exception as e:
                self.logger.warning(f"Failed to get statistics from database: {e}. Using in-memory stats.")
        
        # Otherwise, use in-memory stats
        entity_counts = defaultdict(int)
        for entity in self.entities.values():
            entity_type = entity.__class__.__name__
            entity_counts[entity_type] += 1
            
        relationship_counts = defaultdict(int)
        for rel in self.relationships:
            rel_type = rel.type
            relationship_counts[rel_type] += 1
            
        return {
            "total_entities": len(self.entities),
            "total_relationships": len(self.relationships),
            "entity_counts": dict(entity_counts),
            "relationship_counts": dict(relationship_counts)
        }
        
    def export_to_csv(self, export_dir: str) -> None:
        """
        Export the graph to CSV files.
        
        Args:
            export_dir: Directory to export CSV files to
        """
        if not self.storage.is_connected:
            self.storage.connect()
            
        self.storage.export_to_csv(export_dir)
        
    def import_from_csv(self, import_dir: str) -> None:
        """
        Import the graph from CSV files.
        
        Args:
            import_dir: Directory to import CSV files from
        """
        if not self.storage.is_connected:
            self.storage.connect()
            
        self.storage.import_from_csv(import_dir) 