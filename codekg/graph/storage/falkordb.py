"""
FalkorDB implementation of the graph storage interface.
"""
import os
from typing import Dict, List, Optional, Any
import logging

from .base import BaseGraphStorage


class FalkorDBStorage(BaseGraphStorage):
    """FalkorDB implementation of the graph storage interface."""
    
    def __init__(self, host: str = "localhost", port: int = 6379,
                username: Optional[str] = None, password: Optional[str] = None,
                **kwargs: Any):
        """Initialize the FalkorDB storage."""
        super().__init__(host, port, username, password, **kwargs)
        self.db = None
        
    def connect(self) -> bool:
        """Connect to the FalkorDB database."""
        try:
            # Try to import redis client
            import redis
            
            connection_args = {
                "host": self.host,
                "port": self.port,
                "decode_responses": True
            }
            
            if self.username and self.password:
                connection_args["username"] = self.username
                connection_args["password"] = self.password
                
            self.db = redis.Redis(**connection_args)
            # Test connection
            self.db.ping()
            self.is_connected = True
            self.logger.info(f"Connected to FalkorDB at {self.host}:{self.port}")
            return True
        except ImportError:
            self.logger.error("redis package not found. Please install it with: pip install redis")
            return False
        except Exception as e:
            self.logger.error(f"Failed to connect to FalkorDB: {e}")
            return False
    
    def close(self) -> None:
        """Close the database connection."""
        if self.db:
            self.db.close()
        self.db = None
        self.is_connected = False
        self.logger.info("Disconnected from FalkorDB")
    
    def clear(self) -> None:
        """Clear all data from the database."""
        if not self.is_connected:
            self.connect()
        # Use GRAPH.DELETE to remove the graph
        self.db.execute_command("GRAPH.DELETE", "codekg")
        self.logger.info("Database cleared")
    
    def create_indexes(self) -> None:
        """Create indexes for faster querying."""
        if not self.is_connected:
            self.connect()
            
        # FalkorDB uses different index creation syntax
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
                self.execute_query(index_query)
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
            # Convert parameters to the format FalkorDB expects
            params_list = []
            for key, value in params.items():
                params_list.append(key)
                params_list.append(str(value))
            
            # Execute the query using GRAPH.QUERY command
            result = self.db.execute_command("GRAPH.QUERY", "codekg", query, *params_list)
            
            # Process the results
            processed_results = []
            if result and len(result) >= 2:
                header = result[0]
                data_rows = result[1]
                
                for row in data_rows:
                    record = {}
                    for i, col in enumerate(header):
                        record[col] = row[i]
                    processed_results.append(record)
            
            return processed_results
        except Exception as e:
            self.logger.error(f"Query execution failed: {e}")
            self.logger.error(f"Query: {query}")
            self.logger.error(f"Params: {params}")
            raise
    
    def save_entity(self, entity_id: str, labels: List[str], properties: Dict[str, Any]) -> None:
        """Save an entity to the database."""
        if not self.is_connected:
            self.connect()
            
        # Construct the CREATE query for FalkorDB
        labels_str = ":".join(labels)
        # Handle properties - need to convert to string for FalkorDB
        props_str = ", ".join([f"{k}: ${k}" for k in properties.keys()])
        query = f"CREATE (n:{labels_str} {{id: $id, {props_str}}})"
        
        # Execute the query
        self.execute_query(query, {"id": entity_id, **properties})
    
    def save_relationship(self, source_id: str, target_id: str, rel_type: str, properties: Dict[str, Any]) -> None:
        """Save a relationship to the database."""
        if not self.is_connected:
            self.connect()
            
        # Construct relationship query
        query = f"""
        MATCH (source:CodeResource {{id: $source_id}}), 
              (target:CodeResource {{id: $target_id}})
        CREATE (source)-[r:{rel_type} $properties]->(target)
        """
        
        # Execute the query
        self.execute_query(query, {
            "source_id": source_id, 
            "target_id": target_id,
            "properties": str(properties)  # Convert dict to string for FalkorDB
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
        return int(result[0]["count"]) if result else 0
    
    def count_relationships(self, type_: Optional[str] = None) -> int:
        """Count relationships in the database."""
        if not self.is_connected:
            self.connect()
            
        query = "MATCH ()-[r"
        if type_:
            query += f":{type_}"
        query += "]->() RETURN count(r) as count"
        
        result = self.execute_query(query)
        return int(result[0]["count"]) if result else 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the database."""
        if not self.is_connected:
            self.connect()
            
        # Query for node counts by label
        node_counts_query = """
        MATCH (n)
        RETURN labels(n) AS labels, count(*) AS count
        ORDER BY count DESC
        """
        
        # Query for relationship counts by type
        rel_counts_query = """
        MATCH ()-[r]->()
        RETURN type(r) AS type, count(*) AS count
        ORDER BY count DESC
        """
        
        node_counts = self.execute_query(node_counts_query)
        rel_counts = self.execute_query(rel_counts_query)
        
        # Process node counts
        node_stats = {}
        for item in node_counts:
            for label in item["labels"].split(':'):
                if label == "CodeResource":
                    continue
                node_stats[label] = int(item["count"])
        
        # Process relationship counts
        rel_stats = {item["type"]: int(item["count"]) for item in rel_counts}
        
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
        
        # Similar implementation to MemgraphStorage but adapted for FalkorDB result format
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
                if "n" in results[0] and hasattr(results[0]["n"], "properties"):
                    props = list(results[0]["n"].properties.keys())
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
        
        self.logger.info(f"Exported database to {export_dir}")
    
    def import_from_csv(self, import_dir: str) -> None:
        """Import the database from CSV files."""
        if not self.is_connected:
            self.connect()
            
        # FalkorDB/RedisGraph CSV import implementation
        self.logger.warning("CSV import not fully implemented for FalkorDB") 