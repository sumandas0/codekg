"""
Main CodeKnowledgeGraph class for managing entities and relationships.
"""
from typing import Dict, List, Optional, Set, Any, Type, Union, Tuple
import uuid
import logging
from collections import defaultdict

from gqlalchemy import Memgraph

from .entities import CodeResource
from .relationships import Relationship


class CodeKnowledgeGraph:
    """
    The central class for managing the Code Knowledge Graph.
    Handles entity and relationship management and database interactions.
    """
    
    def __init__(self, memgraph_host: str = "localhost", memgraph_port: int = 7687):
        """
        Initialize a new Code Knowledge Graph.
        
        Args:
            memgraph_host: Hostname of the Memgraph instance
            memgraph_port: Port of the Memgraph instance
        """
        self.entities: Dict[str, CodeResource] = {}
        self.relationships: List[Relationship] = []
        self.db = Memgraph(host=memgraph_host, port=memgraph_port)
        self.logger = logging.getLogger(__name__)
        
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
        """Save the entire graph to the Memgraph database."""
        # Clear existing data (use with caution)
        self.db.execute("MATCH (n) DETACH DELETE n")
        
        # Save entities
        for entity_id, entity in self.entities.items():
            # Convert entity to dict and remove special Pydantic fields
            entity_dict = entity.dict()
            entity_dict.pop("id", None)  # We'll use this as the node ID
            
            # Create Cypher query for the entity
            labels = [entity.__class__.__name__, "CodeResource"]
            labels_str = ":".join(labels)
            
            props_str = ", ".join([f"{k}: ${k}" for k in entity_dict.keys()])
            query = f"CREATE (n:{labels_str} {{id: $id, {props_str}}})"
            
            # Execute query with parameters
            self.db.execute(query, {"id": entity_id, **entity_dict})
        
        # Save relationships
        for rel in self.relationships:
            rel_dict = rel.dict()
            source_id = rel_dict.pop("source")
            target_id = rel_dict.pop("target")
            rel_type = rel_dict.pop("type")
            
            # Create Cypher query for the relationship
            query = f"""
            MATCH (source:CodeResource {{id: $source_id}}), 
                  (target:CodeResource {{id: $target_id}})
            CREATE (source)-[r:{rel_type} $properties]->(target)
            """
            
            # Execute query with parameters
            self.db.execute(query, {
                "source_id": source_id, 
                "target_id": target_id,
                "properties": rel_dict
            })
    
    def load_from_db(self) -> None:
        """Load the graph from the Memgraph database."""
        self.entities.clear()
        self.relationships.clear()
        
        # Load entities
        query = "MATCH (n:CodeResource) RETURN n"
        results = self.db.execute_and_fetch(query)
        
        for record in results:
            node = record["n"]
            # We'd need to map the node properties to the appropriate entity class
            # This is a simplified version
            entity_id = node.properties.get("id")
            if entity_id:
                self.entities[entity_id] = node.properties
        
        # Load relationships
        query = "MATCH (source:CodeResource)-[r]->(target:CodeResource) RETURN source, r, target"
        results = self.db.execute_and_fetch(query)
        
        for record in results:
            source_id = record["source"].properties.get("id")
            target_id = record["target"].properties.get("id")
            rel = record["r"]
            
            if source_id and target_id:
                relationship = Relationship(
                    source=source_id,
                    target=target_id,
                    type=rel.type,
                    properties=rel.properties
                )
                self.relationships.append(relationship)
    
    def query(self, cypher_query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query against the database.
        
        Args:
            cypher_query: The Cypher query to execute
            params: Optional parameters for the query
            
        Returns:
            List of results
        """
        if params is None:
            params = {}
            
        results = self.db.execute_and_fetch(cypher_query, params)
        return [dict(record) for record in results]
    
    def get_statistics(self) -> Dict[str, int]:
        """Get statistics about the graph."""
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