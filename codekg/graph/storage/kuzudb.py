"""
KuzuDB implementation of the graph storage interface.
"""
import os
from typing import Dict, List, Optional, Any
import logging
import uuid

from .base import BaseGraphStorage


class KuzuDBStorage(BaseGraphStorage):
    """KuzuDB implementation of the graph storage interface."""
    
    def __init__(self, db_path: Optional[str] = None, 
                 in_memory: bool = False,
                 buffer_pool_size: int = 512 * 1024 * 1024,
                 max_threads: int = 4,
                 **kwargs: Any):
        """
        Initialize the KuzuDB storage.
        
        Args:
            db_path: Path to the database directory for on-disk mode. If None or empty, uses in-memory mode.
            in_memory: If True, uses in-memory mode regardless of db_path.
            buffer_pool_size: Size of the buffer pool in bytes (default: 512MB).
            max_threads: Maximum number of threads to use (default: 4).
            **kwargs: Additional implementation-specific arguments
        """
        super().__init__(**kwargs)
        self.db_path = db_path if db_path and not in_memory else ":memory:"
        self.in_memory = in_memory or self.db_path == ":memory:" or not db_path
        self.buffer_pool_size = buffer_pool_size
        self.max_threads = max_threads
        self.db = None
        self.conn = None
        
    def connect(self) -> bool:
        """Connect to the KuzuDB database."""
        try:
            import kuzu
            
            if self.in_memory:
                self.logger.info("Creating in-memory Kuzu database")
                # Direct parameter passing instead of using SystemConfig
                self.db = kuzu.Database(
                    buffer_pool_size=self.buffer_pool_size,
                    max_num_threads=self.max_threads
                )
            else:
                self.logger.info(f"Opening Kuzu database at {self.db_path}")
                # Direct parameter passing instead of using SystemConfig
                self.db = kuzu.Database(
                    self.db_path,
                    buffer_pool_size=self.buffer_pool_size,
                    max_num_threads=self.max_threads
                )
            
            self.conn = kuzu.Connection(self.db)
            self.is_connected = True
            self.logger.info(f"Connected to KuzuDB {'in-memory' if self.in_memory else f'at {self.db_path}'}")
            return True
        except ImportError:
            self.logger.error("kuzu package not found. Please install it with: pip install kuzu")
            return False
        except Exception as e:
            self.logger.error(f"Failed to connect to KuzuDB: {e}")
            return False
    
    def close(self) -> None:
        """Close the database connection."""
        # KuzuDB will close connections and free resources when they go out of scope
        self.conn = None
        self.db = None
        self.is_connected = False
        self.logger.info("Disconnected from KuzuDB")
    
    def clear(self) -> None:
        """Clear all data from the database."""
        if not self.is_connected:
            self.connect()
        
        try:
            try:
                self.conn.execute("MATCH (n) DETACH DELETE n")
                self.logger.info("Database cleared with MATCH (n) DETACH DELETE n")
                return
            except Exception as e:
                self.logger.error(f"Standard clear failed: {e}")
                
            # Try separate queries
            try:
                # Delete relationships first
                self.conn.execute("MATCH ()-[r]->() DELETE r")
                self.logger.info("Relationships deleted")
                
                # Then delete nodes
                self.conn.execute("MATCH (n) DELETE n")
                self.logger.info("Nodes deleted")
                return
            except Exception as e:
                self.logger.error(f"Separate delete queries failed: {e}")
                # Just continue with creating the schema
            
            self.logger.info("Proceeding to create schema without clearing old data")
        except Exception as e:
            self.logger.error(f"Failed to clear database: {e}")
        
        # Just continue even if we couldn't clear
    
    def create_indexes(self) -> None:
        """Create necessary indexes for the database."""
        if not self.is_connected:
            self.connect()
            
        # First check if node tables exist, if not create them
        try:
            # Create base node table
            try:
                self.conn.execute("""
                CREATE NODE TABLE CodeResource(
                    id STRING,
                    name STRING,
                    language STRING,
                    qualified_name STRING,
                    description STRING,
                    size INT,
                    access_modifier STRING,
                    is_abstract BOOLEAN,
                    is_interface BOOLEAN,
                    is_static BOOLEAN,
                    is_final BOOLEAN,
                    is_constructor BOOLEAN,
                    PRIMARY KEY (id)
                )
                """)
                self.logger.info("Created CodeResource node table")
            except Exception as e:
                if "already exists" in str(e):
                    self.logger.info("CodeResource node table already exists")
                else:
                    raise
                
            # Create specific node tables
            node_tables = [
                """
                CREATE NODE TABLE File(
                    id STRING, 
                    path STRING,
                    name STRING,
                    language STRING,
                    qualified_name STRING,
                    PRIMARY KEY (id)
                )
                """,
                """
                CREATE NODE TABLE Namespace(
                    id STRING, 
                    name STRING,
                    language STRING,
                    qualified_name STRING,
                    PRIMARY KEY (id)
                )
                """,
                """
                CREATE NODE TABLE Structure(
                    id STRING, 
                    name STRING,
                    language STRING,
                    qualified_name STRING,
                    access_modifier STRING,
                    is_abstract BOOLEAN,
                    is_interface BOOLEAN,
                    is_static BOOLEAN,
                    is_final BOOLEAN,
                    is_constructor BOOLEAN,
                    
                    PRIMARY KEY (id)
                )
                """,
                """
                CREATE NODE TABLE Callable(
                    id STRING, 
                    name STRING,
                    qualified_name STRING,
                    documentation STRING,
                    language STRING,
                    return_type STRING,
                    access_modifier STRING,
                    is_static BOOLEAN,
                    is_abstract BOOLEAN,
                    is_final BOOLEAN,
                    is_constructor BOOLEAN,
                    cyclomatic_complexity INT,
                    lines_of_code INT,
                    signature STRING,
                    PRIMARY KEY (id)
                )
                """,
                """
                CREATE NODE TABLE Variable(
                    id STRING, 
                    name STRING,
                    language STRING,
                    qualified_name STRING,
                    documentation STRING,
                    type STRING,
                    position INT,
                    initial_value STRING,
                    is_constant BOOLEAN,
                    access_modifier STRING,
                    default_value STRING,
                    PRIMARY KEY (id)
                )
                """,
                """
                CREATE NODE TABLE Parameter(
                    id STRING, 
                    name STRING,
                    language STRING,
                    qualified_name STRING,
                    access_modifier STRING,
                    type STRING,
                    position INT,
                    is_optional BOOLEAN,
                    default_value STRING,
                    PRIMARY KEY (id)
                )
                """,
                """
                CREATE NODE TABLE Annotation(
                    id STRING, 
                    name STRING,
                    language STRING,
                    qualified_name STRING,
                    access_modifier STRING,
                    PRIMARY KEY (id)
                )
                """,
                """
                CREATE NODE TABLE Comment(
                    id STRING, 
                    name STRING,
                    language STRING,
                    qualified_name STRING,
                    access_modifier STRING,
                    PRIMARY KEY (id)
                )
                """
            ]
            
            for node_table in node_tables:
                try:
                    self.conn.execute(node_table)
                except Exception as e:
                    if "already exists" in str(e):
                        self.logger.info(f"Node table already exists: {node_table.splitlines()[1].strip()}")
                    else:
                        self.logger.error(f"Failed to create node table: {node_table.splitlines()[1].strip()}, error: {e}")
            
            # Add relationship tables
            relationship_tables = [
                ("DEFINED_IN", "FROM CodeResource TO File"),
                ("CONTAINS", "FROM CodeResource TO CodeResource"),
                ("CALLS", "FROM Callable TO Callable"),
                ("HAS_PARAMETER", "FROM Callable TO CodeResource"),
                ("REFERENCES", "FROM CodeResource TO CodeResource"),
                ("ACCESSES", "FROM Callable TO Variable"),
                ("INHERITS_FROM", "FROM Structure TO Structure"),
                ("IMPLEMENTS", "FROM Structure TO Structure"),
                ("IMPORTS", "FROM File TO CodeResource"),
                ("ANNOTATED_BY", "FROM CodeResource TO CodeResource"),
                ("THROWS", "FROM Callable TO Structure"),
                ("CREATES_INSTANCE", "FROM Callable TO Structure"),
                ("ASSOCIATED_COMMENT", "FROM CodeResource TO CodeResource")
            ]
            
            for rel_name, rel_def in relationship_tables:
                try:
                    self.conn.execute(f"CREATE REL TABLE {rel_name}({rel_def})")
                except Exception as e:
                    if "already exists" in str(e):
                        self.logger.info(f"Relationship table already exists: {rel_name}")
                    else:
                        self.logger.error(f"Failed to create relationship table {rel_name}: {e}")
            
            # Create indexes (KuzuDB automatically creates indexes for primary keys)
            self.logger.info("Created schema and indexes for KuzuDB")
        except Exception as e:
            self.logger.error(f"Failed to create indexes: {e}")
            raise
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return the results."""
        if not self.is_connected:
            self.connect()
            
        if params is None:
            params = {}
            
        try:
            # Execute the query
            result = self.conn.execute(query, params)
            
            # Convert result to list of dictionaries
            results = []
            while result.has_next():
                row = result.get_next()
                if isinstance(row, dict):
                    results.append(row)
                else:
                    # Handle different result formats
                    record = {}
                    for i, col_name in enumerate(result.get_column_names()):
                        record[col_name] = row[i] if i < len(row) else None
                    results.append(record)
                
            return results
        except Exception as e:
            self.logger.error(f"Query execution failed: {e}")
            self.logger.error(f"Query: {query}")
            self.logger.error(f"Params: {params}")
            raise
    
    def save_entity(self, entity_id: str, labels: List[str], properties: Dict[str, Any]) -> None:
        if not self.is_connected:
            self.connect()
        
        try:
            # Primary label is first in the list
            primary_label = labels[0] if labels else "CodeResource"
            
            # Check if we have a table for this node type - if not, use CodeResource
            known_labels = {"File", "Namespace", "Structure", "Callable", "Variable", 
                           "Parameter", "Annotation", "Comment", "CodeResource"}
            
            if primary_label not in known_labels:
                self.logger.warning(f"Unknown node type {primary_label}, using CodeResource instead")
                primary_label = "CodeResource"
            
            # Use a strict whitelist approach
            # Only include properties that we know are safe and necessary
            safe_props = {}
            
            # Always include ID (required)
            sanitized_id = str(entity_id).replace("'", "''")
            safe_props["id"] = f"'{sanitized_id}'"
            
            # List of whitelisted properties by node type
            if primary_label == "File":
                whitelist = ["path", "name", "qualified_name", "language"]
            else:
                whitelist = ["name", "qualified_name", "language", "access_modifier", 
                            "is_abstract", "is_interface", "is_static", "return_type", 
                            "signature", "type"]
            
            # Add safe properties from whitelist
            for prop in whitelist:
                if prop in properties and properties[prop] is not None:
                    value = properties[prop]
                    if isinstance(value, str):
                        sanitized_value = value.replace("'", "''")
                        safe_props[prop] = f"'{sanitized_value}'"
                    elif isinstance(value, bool):
                        safe_props[prop] = str(value).lower()  # 'true' or 'false'
                    elif isinstance(value, (int, float)):
                        safe_props[prop] = str(value)
            
            # Ensure qualified_name is not null (required for most lookups)
            if "qualified_name" not in safe_props and primary_label != "File":
                safe_props["qualified_name"] = f"'{primary_label}_{sanitized_id}'"
                
            # Ensure path for File nodes
            if primary_label == "File" and "path" not in safe_props:
                safe_props["path"] = f"'unknown_path_{sanitized_id}'"
            
            props_parts = [f"{key}: {value}" for key, value in safe_props.items()]
            props_str = ", ".join(props_parts)
            
            # Create the node
            query = f"CREATE (:{primary_label} {{{props_str}}});"
            self.logger.debug(f"Executing query: {query}")
            
            self.conn.execute(query)            
        except Exception as e:
            self.logger.error(f"Failed to save entity {entity_id}: {e}")
    
    def save_relationship(self, source_id: str, target_id: str, rel_type: str, properties: Dict[str, Any]) -> None:
        """Save a relationship to the database."""
        if not self.is_connected:
            self.connect()
        
        try:
            # Determine correct node labels based on relationship type
            # These must match the schema defined in create_indexes
            source_label = "CodeResource"
            target_label = "CodeResource"
            
            # Map relationship types to the correct source and target labels
            rel_schemas = {
                "DEFINED_IN": ("CodeResource", "File"),
                "CONTAINS": ("CodeResource", "CodeResource"),
                "CALLS": ("Callable", "Callable"),
                "HAS_PARAMETER": ("Callable", "CodeResource"),
                "REFERENCES": ("CodeResource", "CodeResource"),
                "ACCESSES": ("Callable", "Variable"),
                "INHERITS_FROM": ("Structure", "Structure"),
                "IMPLEMENTS": ("Structure", "Structure"),
                "IMPORTS": ("File", "CodeResource"),
                "ANNOTATED_BY": ("CodeResource", "CodeResource"),
                "THROWS": ("Callable", "Structure"),
                "CREATES_INSTANCE": ("Callable", "Structure"),
                "ASSOCIATED_COMMENT": ("CodeResource", "CodeResource")
            }
            
            if rel_type in rel_schemas:
                source_label, target_label = rel_schemas[rel_type]
            
            sanitized_source_id = source_id.replace("'", "''")
            sanitized_target_id = target_id.replace("'", "''")
            
            # Use MERGE for nodes to prevent duplicate primary key errors
            try:
                # First create nodes with MERGE to handle duplicates
                query1 = f"MERGE (a:{source_label} {{id: '{sanitized_source_id}'}})"
                query2 = f"MERGE (b:{target_label} {{id: '{sanitized_target_id}'}})"
                
                self.conn.execute(query1)
                self.conn.execute(query2)
                
                # Then try to create relationship with MATCH
                query3 = f"""
                MATCH (a:{source_label} {{id: '{sanitized_source_id}'}}), 
                      (b:{target_label} {{id: '{sanitized_target_id}'}})
                CREATE (a)-[:{rel_type}]->(b)
                """
                self.conn.execute(query3)
                return
            except Exception as e:
                error_msg = str(e)
                if "duplicated primary key" in error_msg:
                    self.logger.warning(f"Duplicate key detected, continuing with relationship creation")
                    # Continue with trying to create just the relationship
                else:
                    self.logger.error(f"Failed to merge nodes and create relationship: {e}")
                    # Continue to next approach
            
            # Try a different approach using just MATCH to find existing nodes
            try:
                query = f"""
                MATCH (a:{source_label} {{id: '{sanitized_source_id}'}}), 
                      (b:{target_label} {{id: '{sanitized_target_id}'}})
                CREATE (a)-[:{rel_type}]->(b)
                """
                self.conn.execute(query)
                return
            except Exception as e:
                self.logger.error(f"Failed to match nodes and create relationship: {e}")
                # Continue to next approach
                
        except Exception as e:
            self.logger.error(f"Failed to save relationship {rel_type} from {source_id} to {target_id}: {e}")
        
        # Just continue instead of raising an exception
        return
    
    def count_nodes(self, label: Optional[str] = None) -> int:
        """Count nodes in the database."""
        if not self.is_connected:
            self.connect()
            
        try:
            if label:
                query = f"MATCH (n:{label}) RETURN count(n) as count"
            else:
                query = "MATCH (n) RETURN count(n) as count"
            
            result = self.execute_query(query)
            return result[0]["count"] if result else 0
        except Exception as e:
            self.logger.error(f"Failed to count nodes: {e}")
            return 0
    
    def count_relationships(self, type_: Optional[str] = None) -> int:
        """Count relationships in the database."""
        if not self.is_connected:
            self.connect()
            
        try:
            if type_:
                query = f"MATCH ()-[r:{type_}]->() RETURN count(r) as count"
            else:
                query = "MATCH ()-[r]->() RETURN count(r) as count"
            
            result = self.execute_query(query)
            return result[0]["count"] if result else 0
        except Exception as e:
            self.logger.error(f"Failed to count relationships: {e}")
            return 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the database."""
        if not self.is_connected:
            self.connect()
            
        try:
            # Use labels instead of table names
            node_stats = {}
            try:
                node_labels_query = "MATCH (n) RETURN DISTINCT labels(n) AS label, count(*) as count"
                node_tables = self.execute_query(node_labels_query)
                
                for table in node_tables:
                    label = table.get("label")
                    count = table.get("count", 0)
                    if label:
                        if isinstance(label, list):
                            for l in label:
                                if l != "CodeResource":  # Avoid double counting
                                    node_stats[l] = count
                        else:
                            node_stats[label] = count
            except Exception as e:
                self.logger.error(f"Error getting node statistics: {e}")
            
            # Get relationship table statistics - simplify since we don't have type()
            rel_stats = {}
            
            # For KuzuDB, we'll just report the relationship counts by table rather than by type
            # Since type() function isn't available in KuzuDB
            try:
                # Just count overall relationships
                rel_count_query = "MATCH ()-[r]->() RETURN count(r) as count"
                rel_count = self.execute_query(rel_count_query)
                
                if rel_count and "count" in rel_count[0]:
                    rel_stats["TOTAL"] = rel_count[0]["count"]
            except Exception as e:
                self.logger.error(f"Error getting relationship statistics: {e}")
            
            return {
                "total_nodes": sum(node_stats.values()) if node_stats else 0,
                "total_relationships": sum(rel_stats.values()) if rel_stats else 0,
                "node_counts": node_stats,
                "relationship_counts": rel_stats
            }
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {
                "total_nodes": 0,
                "total_relationships": 0,
                "node_counts": {},
                "relationship_counts": {}
            }
    
    def export_to_csv(self, export_dir: str) -> None:
        """Export the database to CSV files."""
        if not self.is_connected:
            self.connect()
            
        os.makedirs(export_dir, exist_ok=True)
        
        try:
            # Get node labels instead of tables
            node_labels_query = "MATCH (n) RETURN DISTINCT labels(n) AS labels"
            node_tables = self.execute_query(node_labels_query)
            
            # Export each node type
            for record in node_tables:
                labels = record.get("labels", [])
                if isinstance(labels, list):
                    for label in labels:
                        if label == "CodeResource":
                            continue  # Skip base class
                            
                        csv_path = os.path.join(export_dir, f"{label.lower()}.csv")
                        
                        # Use KuzuDB's COPY command
                        export_query = f"""
                        COPY (MATCH (n:{label}) RETURN n.*) 
                        TO '{csv_path}'
                        """
                        try:
                            self.conn.execute(export_query)
                            self.logger.info(f"Exported {label} nodes to {csv_path}")
                        except Exception as e:
                            self.logger.error(f"Failed to export {label} nodes: {e}")
                else:
                    label = labels
                    if label and label != "CodeResource":
                        csv_path = os.path.join(export_dir, f"{label.lower()}.csv")
                        
                        # Use KuzuDB's COPY command
                        export_query = f"""
                        COPY (MATCH (n:{label}) RETURN n.*) 
                        TO '{csv_path}'
                        """
                        try:
                            self.conn.execute(export_query)
                            self.logger.info(f"Exported {label} nodes to {csv_path}")
                        except Exception as e:
                            self.logger.error(f"Failed to export {label} nodes: {e}")
            
            # Instead of querying relationships by type, export all relationships
            try:
                all_rels_csv_path = os.path.join(export_dir, "relationships.csv")
                export_query = """
                COPY (MATCH (src)-[r]->(dst) 
                     RETURN src.id AS source_id, dst.id AS target_id)
                TO '{}'
                """.format(all_rels_csv_path)
                self.conn.execute(export_query)
                self.logger.info(f"Exported all relationships to {all_rels_csv_path}")
            except Exception as e:
                self.logger.error(f"Failed to export relationships: {e}")
            
            self.logger.info(f"Database exported to {export_dir}")
        except Exception as e:
            self.logger.error(f"Failed to export database to CSV: {e}")
            raise
    
    def import_from_csv(self, import_dir: str) -> None:
        """Import the database from CSV files."""
        if not self.is_connected:
            self.connect()
            
        try:
            # First create the schema
            self.create_indexes()
            
            # Get list of CSV files in the import directory
            csv_files = [f for f in os.listdir(import_dir) if f.endswith('.csv')]
            
            # Import node tables first
            node_tables = self.execute_query("SHOW NODE TABLES")
            node_table_names = [table.get("name").lower() for table in node_tables if table.get("name")]
            
            for table_name in node_table_names:
                csv_file = f"{table_name.lower()}.csv"
                if csv_file in csv_files:
                    csv_path = os.path.join(import_dir, csv_file)
                    
                    # Use KuzuDB's COPY command to import
                    import_query = f"""
                    COPY {table_name} FROM '{csv_path}'
                    """
                    self.conn.execute(import_query)
                    self.logger.info(f"Imported {table_name} nodes from {csv_path}")
            
            # Then import relationship tables
            rel_tables = self.execute_query("SHOW REL TABLES")
            rel_table_names = [table.get("name").lower() for table in rel_tables if table.get("name")]
            
            for table_name in rel_table_names:
                csv_file = f"{table_name.lower()}.csv"
                if csv_file in csv_files:
                    csv_path = os.path.join(import_dir, csv_file)
                    
                    # For relationships, we need to match source and target nodes
                    import_query = f"""
                    COPY {table_name} FROM '{csv_path}'
                    """
                    self.conn.execute(import_query)
                    self.logger.info(f"Imported {table_name} relationships from {csv_path}")
            
            self.logger.info(f"Database imported from {import_dir}")
        except Exception as e:
            self.logger.error(f"Failed to import database from CSV: {e}")
            raise 