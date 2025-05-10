"""
Memgraph implementation of the graph storage interface.
"""
import os
from typing import Dict, List, Optional, Any
import logging

from .base import BaseGraphStorage


class MemgraphStorage(BaseGraphStorage):
    """Memgraph implementation of the graph storage interface."""
    
    def __init__(self, host: str = "localhost", port: int = 7687,
                username: Optional[str] = None, password: Optional[str] = None,
                **kwargs: Any):
        """Initialize the Memgraph storage."""
        super().__init__(host, port, username, password, **kwargs)
        self.db = None
        
    def connect(self) -> bool:
        """Connect to the Memgraph database."""
        try:
            from gqlalchemy import Memgraph
            
            connection_args = {
                "host": self.host,
                "port": self.port
            }
            
            if self.username and self.password:
                connection_args["username"] = self.username
                connection_args["password"] = self.password
                
            self.db = Memgraph(**connection_args)
            self.is_connected = True
            self.logger.info(f"Connected to Memgraph at {self.host}:{self.port}")
            return True
        except ImportError:
            self.logger.error("gqlalchemy package not found. Please install it with: pip install gqlalchemy")
            return False
        except Exception as e:
            self.logger.error(f"Failed to connect to Memgraph: {e}")
            return False
    
    def close(self) -> None:
        """Close the database connection."""
        self.db = None
        self.is_connected = False
        self.logger.info("Disconnected from Memgraph")
    
    def clear(self) -> None:
        """Clear all data from the database."""
        if not self.is_connected:
            self.connect()
        self.db.execute("MATCH (n) DETACH DELETE n")
        self.logger.info("Database cleared")
    
    def create_indexes(self) -> None:
        """Create indexes for faster querying."""
        if not self.is_connected:
            self.connect()
            
        indexes = [
            "CREATE INDEX ON :CodeResource(id)",
            "CREATE INDEX ON :CodeResource(qualified_name)",
            "CREATE INDEX ON :File(path)",
            "CREATE INDEX ON :Namespace(qualified_name)",
            "CREATE INDEX ON :Structure(qualified_name)",
            "CREATE INDEX ON :Callable(qualified_name)",
            "CREATE INDEX ON :Variable(qualified_name)"
        ]
        
        for index_query in indexes:
            try:
                self.db.execute(index_query)
                self.logger.info(f"Created index: {index_query}")
            except Exception as e:
                self.logger.warning(f"Failed to create index {index_query}: {e}")
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return the results."""
        if not self.is_connected:
            self.connect()
            
        if params is None:
            params = {}
            
        try:
            results = self.db.execute_and_fetch(query, params)
            return [dict(record) for record in results]
        except Exception as e:
            self.logger.error(f"Query execution failed: {e}")
            self.logger.error(f"Query: {query}")
            self.logger.error(f"Params: {params}")
            raise
    
    def save_entity(self, entity_id: str, labels: List[str], properties: Dict[str, Any]) -> None:
        """Save an entity to the database."""
        if not self.is_connected:
            self.connect()
            
        labels_str = ":".join(labels)
        props_str = ", ".join([f"{k}: ${k}" for k in properties.keys()])
        query = f"CREATE (n:{labels_str} {{id: $id, {props_str}}})"
        
        self.execute_query(query, {"id": entity_id, **properties})
    
    def save_relationship(self, source_id: str, target_id: str, rel_type: str, properties: Dict[str, Any]) -> None:
        """Save a relationship to the database."""
        if not self.is_connected:
            self.connect()
            
        query = f"""
        MATCH (source:CodeResource {{id: $source_id}}), 
              (target:CodeResource {{id: $target_id}})
        CREATE (source)-[r:{rel_type} $properties]->(target)
        """
        
        self.execute_query(query, {
            "source_id": source_id, 
            "target_id": target_id,
            "properties": properties
        })
    
    def count_nodes(self, label: Optional[str] = None) -> int:
        """Count nodes in the database."""
        if not self.is_connected:
            self.connect()
            
        query = "MATCH (n"
        if label:
            query += f":{label}"
        query += ") RETURN count(n) as count"
        
        result = self.execute_query(query)
        return result[0]["count"] if result else 0
    
    def count_relationships(self, type_: Optional[str] = None) -> int:
        """Count relationships in the database."""
        if not self.is_connected:
            self.connect()
            
        query = "MATCH ()-[r"
        if type_:
            query += f":{type_}"
        query += "]->() RETURN count(r) as count"
        
        result = self.execute_query(query)
        return result[0]["count"] if result else 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the database."""
        if not self.is_connected:
            self.connect()
            
        node_counts_query = """
        MATCH (n)
        RETURN labels(n) AS labels, count(*) AS count
        ORDER BY count DESC
        """
        
        rel_counts_query = """
        MATCH ()-[r]->()
        RETURN type(r) AS type, count(*) AS count
        ORDER BY count DESC
        """
        
        node_counts = self.execute_query(node_counts_query)
        rel_counts = self.execute_query(rel_counts_query)
        
        node_stats = {}
        for item in node_counts:
            for label in item["labels"]:
                if label == "CodeResource":
                    continue
                node_stats[label] = item["count"]
        
        rel_stats = {item["type"]: item["count"] for item in rel_counts}
        
        return {
            "total_nodes": self.count_nodes(),
            "total_relationships": self.count_relationships(),
            "node_counts": node_stats,
            "relationship_counts": rel_stats
        }
    
    def export_to_csv(self, export_dir: str) -> None:
        """Export the database to CSV files."""
        if not self.is_connected:
            self.connect()
            
        os.makedirs(export_dir, exist_ok=True)
        
        # Export nodes
        node_types = [
            "File", "Namespace", "Structure", "Callable",
            "Parameter", "Variable", "Annotation", "Comment"
        ]
        
        for node_type in node_types:
            query = f"""
            MATCH (n:{node_type})
            RETURN n
            """
            
            results = self.execute_query(query)
            if not results:
                continue
                
            filepath = os.path.join(export_dir, f"{node_type.lower()}.csv")
            
            with open(filepath, 'w') as f:
                # Write header
                props = [k for k in results[0]["n"].properties.keys()]
                f.write("id," + ",".join(props) + "\n")
                
                # Write rows
                for result in results:
                    node = result["n"]
                    row = [str(node.id)]
                    for prop in props:
                        val = node.properties.get(prop, "")
                        # Escape commas and quotes
                        if isinstance(val, str):
                            val = f'"{val.replace("\"", "\"\"")}"'
                        row.append(str(val))
                    f.write(",".join(row) + "\n")
        
        # Export relationships
        rel_types = [
            "DEFINED_IN", "CONTAINS", "CALLS", "HAS_PARAMETER",
            "REFERENCES", "ACCESSES", "INHERITS_FROM", "IMPLEMENTS",
            "IMPORTS", "ANNOTATED_BY", "THROWS", "CREATES_INSTANCE",
            "ASSOCIATED_COMMENT"
        ]
        
        for rel_type in rel_types:
            query = f"""
            MATCH (source)-[r:{rel_type}]->(target)
            RETURN source.id AS source_id, target.id AS target_id, r
            """
            
            results = self.execute_query(query)
            if not results:
                continue
                
            filepath = os.path.join(export_dir, f"{rel_type.lower()}.csv")
            
            with open(filepath, 'w') as f:
                # Check if the first relationship has any properties
                if results and results[0]["r"].properties:
                    props = [k for k in results[0]["r"].properties.keys()]
                    f.write("source_id,target_id," + ",".join(props) + "\n")
                    
                    for result in results:
                        rel = result["r"]
                        row = [str(result["source_id"]), str(result["target_id"])]
                        for prop in props:
                            val = rel.properties.get(prop, "")
                            if isinstance(val, str):
                                val = f'"{val.replace("\"", "\"\"")}"'
                            row.append(str(val))
                        f.write(",".join(row) + "\n")
                else:
                    # Simple relationships without properties
                    f.write("source_id,target_id\n")
                    for result in results:
                        f.write(f"{result['source_id']},{result['target_id']}\n")
        
        self.logger.info(f"Exported database to {export_dir}")
    
    def import_from_csv(self, import_dir: str) -> None:
        """Import the database from CSV files."""
        if not self.is_connected:
            self.connect()
            
        # Implementation would depend on Memgraph's CSV import capabilities
        self.logger.warning("CSV import not fully implemented for Memgraph") 