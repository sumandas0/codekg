# Database Storage Support in CodeKG

CodeKG now supports multiple graph database backends for storing and querying code knowledge graphs. This document explains how to configure and use different database backends.

## Supported Database Backends

Currently, CodeKG supports the following database backends:

1. **Memgraph** (default) - An in-memory graph database
2. **FalkorDB** (formerly RedisGraph) - A Redis module that adds graph database capabilities
3. **Neo4j** - A popular graph database platform
4. **KuzuDB** - A high-performance graph database supporting on-disk and in-memory modes

## Configuration

You can specify which database to use through the CLI or when creating a `CodeKnowledgeGraph` instance programmatically.

### Command-Line Interface

When using the CLI, you can specify the database type and connection settings using these options:

```bash
# Parse a Java codebase and store it in Memgraph (default)
python -m codekg.cli parse /path/to/java/code --language java

# Parse a Java codebase and store it in FalkorDB
python -m codekg.cli parse /path/to/java/code --language java --db-type falkordb --db-port 6379

# Parse a Java codebase and store it in Neo4j with authentication
python -m codekg.cli parse /path/to/java/code --language java --db-type neo4j --db-user neo4j --db-pass password --db-name codekg

# Parse a Java codebase and store it in KuzuDB (on-disk mode)
python -m codekg.cli parse /path/to/java/code --language java --db-type kuzudb --db-path ./kuzudb_data

# Parse a Java codebase and store it in KuzuDB (in-memory mode)
python -m codekg.cli parse /path/to/java/code --language java --db-type kuzudb --db-in-memory
```

The available CLI options for database configuration are:

- `--db-type`: Database type (`memgraph`, `falkordb`, `neo4j`, or `kuzudb`) [default: memgraph]
- `--db-host`: Database server hostname [default: localhost]
- `--db-port`: Database server port (if not specified, uses default port for the selected database type)
- `--db-user`: Username for authentication (optional)
- `--db-pass`: Password for authentication (optional)
- `--db-name`: Database name for Neo4j (optional, default: neo4j)
- `--db-path`: Database path for KuzuDB on-disk mode (optional)
- `--db-in-memory`: Use in-memory mode for KuzuDB (flag)

### Programmatic Usage

When creating a `CodeKnowledgeGraph` instance in your code, you can specify the database type and connection settings:

```python
from codekg.core import CodeKnowledgeGraph

# Use Memgraph (default)
graph = CodeKnowledgeGraph()

# Use FalkorDB
graph = CodeKnowledgeGraph(
    storage_type="falkordb",
    storage_config={
        "host": "localhost",
        "port": 6379
    }
)

# Use Neo4j with authentication
graph = CodeKnowledgeGraph(
    storage_type="neo4j",
    storage_config={
        "host": "localhost",
        "port": 7687,
        "username": "neo4j",
        "password": "password",
        "database": "codekg"
    }
)

# Use KuzuDB (on-disk mode)
graph = CodeKnowledgeGraph(
    storage_type="kuzudb",
    storage_config={
        "db_path": "./kuzudb_data",
        "buffer_pool_size": 1024 * 1024 * 1024  # 1GB buffer pool
    }
)

# Use KuzuDB (in-memory mode)
graph = CodeKnowledgeGraph(
    storage_type="kuzudb",
    storage_config={
        "in_memory": True
    }
)
```

## Installation Requirements

Each database backend requires specific dependencies to be installed:

### Memgraph

```bash
pip install gqlalchemy
```

### FalkorDB

```bash
pip install redis
```

### Neo4j

```bash
pip install neo4j
```

### KuzuDB

```bash
pip install kuzu
```

## Database Setup

### Memgraph

1. Install Memgraph using Docker:
   ```bash
   docker run -it -p 7687:7687 -p 3000:3000 -v mg_lib:/var/lib/memgraph memgraph/memgraph-platform
   ```

2. Connect to Memgraph Lab at http://localhost:3000 to visualize and query your graph.

### FalkorDB

1. Install FalkorDB using Docker:
   ```bash
   docker run -p 6379:6379 -it --rm falkordb/falkordb:latest
   ```

2. You can use RedisInsight or any Redis client to connect to FalkorDB.

### Neo4j

1. Install Neo4j using Docker:
   ```bash
   docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest
   ```

2. Access Neo4j Browser at http://localhost:7474 to visualize and query your graph.

### KuzuDB

1. Install KuzuDB via pip:
   ```bash
   pip install kuzu
   ```

2. No separate server setup is required as KuzuDB is an embedded database that runs within your application.

3. For on-disk mode, specify a database path:
   ```bash
   python -m codekg.cli parse /path/to/code --db-type kuzudb --db-path ./kuzudb_data
   ```

4. For in-memory mode, use the `--db-in-memory` flag:
   ```bash
   python -m codekg.cli parse /path/to/code --db-type kuzudb --db-in-memory
   ```

## Example Usage

### Parsing and Storing Code

```python
from codekg.core import CodeKnowledgeGraph
from codekg.parsers import JavaParser

# Create a graph with FalkorDB storage
graph = CodeKnowledgeGraph(
    storage_type="falkordb",
    storage_config={"host": "localhost", "port": 6379}
)

# Create a graph with KuzuDB storage (on-disk)
graph = CodeKnowledgeGraph(
    storage_type="kuzudb",
    storage_config={"db_path": "./kuzudb_data"}
)

# Parse Java code
parser = JavaParser()
parser.parse_directory("/path/to/java/code", graph)

# Save to database
graph.save_to_db()
```

### Querying the Graph

```python
# Execute a Cypher query
results = graph.query("""
MATCH (c:Callable)-[:CALLS]->(target:Callable)
RETURN c.qualified_name as caller, target.qualified_name as callee
LIMIT 10
""")

for result in results:
    print(f"{result['caller']} calls {result['callee']}")
```

### Exporting and Importing

```python
# Export to CSV
graph.export_to_csv("/path/to/export/directory")

# Import from CSV
graph.import_from_csv("/path/to/import/directory")
```

## Switching Between Databases

You can easily migrate your graph data between different database backends:

```python
# Export from Memgraph
memgraph = CodeKnowledgeGraph(storage_type="memgraph")
memgraph.export_to_csv("/tmp/codekg-export")

# Import to KuzuDB
kuzu_graph = CodeKnowledgeGraph(
    storage_type="kuzudb", 
    storage_config={"db_path": "./kuzudb_data"}
)
kuzu_graph.import_from_csv("/tmp/codekg-export")
```

## KuzuDB-Specific Features

KuzuDB offers some specific advantages:

1. **Embedded operation**: No separate server required, runs within your application
2. **Storage modes**: Supports both on-disk persistence and in-memory operation
3. **Performance**: Optimized for high performance with large graphs
4. **Schema-based**: Uses a structured property graph model with strong typing
5. **Cypher compatible**: Supports a Cypher-like query language 