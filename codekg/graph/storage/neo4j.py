"""
Neo4j implementation of the graph storage interface.
"""
import os
from typing import Dict, List, Optional, Any
import logging

from .base import BaseGraphStorage


class Neo4jStorage(BaseGraphStorage):
    """Neo4j implementation of the graph storage interface."""
    
    def __init__(self, host: str = "localhost", port: int = 7687,
                username: Optional[str] = "neo4j", password: Optional[str] = "neo4j",
                database: str = "neo4j", **kwargs: Any):
        """Initialize the Neo4j storage."""
        super().__init__(host, port, username, password, **kwargs)
        self.database = database
        self.driver = None
        
    def connect(self) -> bool:
        """Connect to the Neo4j database."""
        try:
            # Try to import neo4j driver
            from neo4j import GraphDatabase
            
            uri = f"neo4j://{self.host}:{self.port}"
            
            self.driver = GraphDatabase.driver(
                uri, 
                auth=(self.username, self.password) if self.username and self.password else None
            )
            
            # Test connection
            with self.driver.session(database=self.database) as session:
                session.run("RETURN 1")
            
            self.is_connected = True
            self.logger.info(f"Connected to Neo4j at {uri}")
            return True
        except ImportError:
            self.logger.error("neo4j package not found. Please install it with: pip install neo4j")
            return False
        except Exception as e:
            self.logger.error(f"Failed to connect to Neo4j: {e}")
            return False
    
    def close(self) -> None:
        """Close the database connection."""
        if self.driver:
            self.driver.close()
        self.driver = None
        self.is_connected = False
        self.logger.info("Disconnected from Neo4j")
    
    def clear(self) -> None:
        """Clear all data from the database."""
        if not self.is_connected:
            self.connect()
        
        with self.driver.session(database=self.database) as session:
            session.run("MATCH (n) DETACH DELETE n")
        
        self.logger.info("Database cleared")
    
    def create_indexes(self) -> None:
        """Create indexes for faster querying."""
        if not self.is_connected:
            self.connect()
            
        indexes = [
            "CREATE INDEX code_resource_id_idx IF NOT EXISTS FOR (n:CodeResource) ON (n.id)",
            "CREATE INDEX code_resource_qname_idx IF NOT EXISTS FOR (n:CodeResource) ON (n.qualified_name)",
            "CREATE INDEX file_path_idx IF NOT EXISTS FOR (n:File) ON (n.path)",
            "CREATE INDEX namespace_qname_idx IF NOT EXISTS FOR (n:Namespace) ON (n.qualified_name)",
            "CREATE INDEX structure_qname_idx IF NOT EXISTS FOR (n:Structure) ON (n.qualified_name)",
            "CREATE INDEX callable_qname_idx IF NOT EXISTS FOR (n:Callable) ON (n.qualified_name)",
            "CREATE INDEX variable_qname_idx IF NOT EXISTS FOR (n:Variable) ON (n.qualified_name)"
        ]
        
        with self.driver.session(database=self.database) as session:
            for index_query in indexes:
                try:
                    session.run(index_query)
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
            with self.driver.session(database=self.database) as session:
                result = session.run(query, params)
                return [dict(record) for record in result]
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
        
        with self.driver.session(database=self.database) as session:
            session.run(query, {"id": entity_id, **properties})
    
    def save_relationship(self, source_id: str, target_id: str, rel_type: str, properties: Dict[str, Any]) -> None:
        """Save a relationship to the database."""
        if not self.is_connected:
            self.connect()
            
        query = f"""
        MATCH (source:CodeResource {{id: $source_id}}), 
              (target:CodeResource {{id: $target_id}})
        CREATE (source)-[r:{rel_type} $properties]->(target)
        """
        
        with self.driver.session(database=self.database) as session:
            session.run(query, {
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
        
        with self.driver.session(database=self.database) as session:
            result = session.run(query)
            record = result.single()
            return record["count"] if record else 0
    
    def count_relationships(self, type_: Optional[str] = None) -> int:
        """Count relationships in the database."""
        if not self.is_connected:
            self.connect()
            
        query = "MATCH ()-[r"
        if type_:
            query += f":{type_}"
        query += "]->() RETURN count(r) as count"
        
        with self.driver.session(database=self.database) as session:
            result = session.run(query)
            record = result.single()
            return record["count"] if record else 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the database."""
        if not self.is_connected:
            self.connect()
            
        node_counts_query = """
        MATCH (n)
        WITH labels(n) AS labels, count(*) AS count
        UNWIND labels AS label
        RETURN label, sum(count) AS count
        ORDER BY count DESC
        """
        
        rel_counts_query = """
        MATCH ()-[r]->()
        RETURN type(r) AS type, count(*) AS count
        ORDER BY count DESC
        """
        
        with self.driver.session(database=self.database) as session:
            node_counts = [dict(record) for record in session.run(node_counts_query)]
            rel_counts = [dict(record) for record in session.run(rel_counts_query)]
            
            node_stats = {}
            for item in node_counts:
                if item["label"] == "CodeResource":
                    continue
                node_stats[item["label"]] = item["count"]
            
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
        
        # For Neo4j we could use the built-in APOC procedures for CSV export
        # But for consistency we'll implement similar logic to the other adapters
        
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
            
            with self.driver.session(database=self.database) as session:
                results = [dict(record) for record in session.run(query)]
                
                if not results:
                    continue
                    
                filepath = os.path.join(export_dir, f"{node_type.lower()}.csv")
                
                with open(filepath, 'w') as f:
                    # Write header - assuming all nodes of same type have same properties
                    if "n" in results[0]:
                        node = results[0]["n"]
                        props = list(node.keys())
                        f.write("id," + ",".join(props) + "\n")
                        
                        # Write rows
                        for result in results:
                            node = result["n"]
                            node_id = node.id  # Neo4j internal ID
                            row = [str(node_id)]
                            for prop in props:
                                val = node.get(prop, "")
                                if isinstance(val, str):
                                    val = f'"{val.replace("\"", "\"\"")}"'
                                row.append(str(val))
                            f.write(",".join(row) + "\n")
        
        self.logger.info(f"Exported database to {export_dir}")
    
    def import_from_csv(self, import_dir: str) -> None:
        """Import the database from CSV files."""
        if not self.is_connected:
            self.connect()
            
        # For Neo4j, we could use LOAD CSV
        self.logger.warning("CSV import not fully implemented for Neo4j") 