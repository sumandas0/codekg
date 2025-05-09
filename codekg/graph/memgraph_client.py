"""
Memgraph database client for CodeKG.
"""
from typing import Dict, List, Optional, Any
import logging
import os

from gqlalchemy import Memgraph


class MemgraphClient:
    """
    Client for interacting with Memgraph database.
    Provides methods for storing and querying the code knowledge graph.
    """
    
    def __init__(self, host: str = "localhost", port: int = 7687,
                username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize the Memgraph client.
        
        Args:
            host: Memgraph server hostname
            port: Memgraph server port
            username: Optional username for authentication
            password: Optional password for authentication
        """
        self.logger = logging.getLogger(__name__)
        
        connection_args = {
            "host": host,
            "port": port
        }
        
        if username and password:
            connection_args["username"] = username
            connection_args["password"] = password
            
        try:
            self.db = Memgraph(**connection_args)
            self.logger.info(f"Connected to Memgraph at {host}:{port}")
        except Exception as e:
            self.logger.error(f"Failed to connect to Memgraph: {e}")
            raise
    
    def create_indexes(self) -> None:
        """Create indexes for faster querying."""
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
    
    def clear_database(self) -> None:
        """Clear all data from the database. Use with caution!"""
        self.db.execute("MATCH (n) DETACH DELETE n")
        self.logger.info("Database cleared")
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return the results.
        
        Args:
            query: Cypher query string
            params: Optional parameters for the query
            
        Returns:
            List of result records as dictionaries
        """
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
    
    def count_nodes(self, label: Optional[str] = None) -> int:
        """
        Count nodes in the database, optionally filtered by label.
        
        Args:
            label: Optional node label to filter by
            
        Returns:
            Count of matching nodes
        """
        query = "MATCH (n"
        if label:
            query += f":{label}"
        query += ") RETURN count(n) as count"
        
        result = self.execute_query(query)
        return result[0]["count"] if result else 0
    
    def count_relationships(self, type_: Optional[str] = None) -> int:
        """
        Count relationships in the database, optionally filtered by type.
        
        Args:
            type_: Optional relationship type to filter by
            
        Returns:
            Count of matching relationships
        """
        query = "MATCH ()-[r"
        if type_:
            query += f":{type_}"
        query += "]->() RETURN count(r) as count"
        
        result = self.execute_query(query)
        return result[0]["count"] if result else 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the database.
        
        Returns:
            Dictionary with statistics
        """
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
        """
        Export the database to CSV files.
        
        Args:
            export_dir: Directory to export CSV files to
        """
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
        """
        Import the database from CSV files.
        
        Args:
            import_dir: Directory containing CSV files to import
        """
        # Implementation would follow a similar pattern to export_to_csv but in reverse
        # Reading CSV files and using LOAD CSV or equivalent to populate the database
        pass 