# Code Knowledge Graph (CodeKG)

An extensible knowledge graph framework for representing codebases as a graph, capturing code structure, relationships, and dependencies.

## Overview

CodeKG allows you to:
- Parse source code into a rich knowledge graph
- Perform powerful queries and analyses on code structure
- Understand dependencies and relationships between code components
- Support for multiple programming languages (Java and Python, with planned support for JavaScript, C++, and Go)

## Project Structure

- `codekg/`: Main package
  - `core/`: Core entities and relationships
  - `parsers/`: Language-specific parsers using Tree-sitter
  - `graph/`: Graph database integration with Memgraph and KuzuDB
  - `analysis/`: Analysis modules and utilities
  - `utils/`: Common utilities
- `docker/`: Docker Compose configurations for graph databases

## Requirements

- Python 3.8+
- Graph database (Memgraph or KuzuDB)
- Docker (optional, for running databases)
- Tree-sitter and language grammars (automatically installed via requirements.txt)

## Installation

```bash
pip install -r requirements.txt
```

## Docker-based Graph Databases

CodeKG supports multiple graph database backends. You can easily run them using Docker:

```bash
# Start Memgraph and its web UI
docker-compose -f docker/docker-compose.yaml up memgraph lab

# Start KuzuDB Explorer 
docker-compose -f docker/docker-compose.yaml up kuzudb-explorer

# Or start all services
docker-compose -f docker/docker-compose.yaml up
```

See `docker/README.md` for detailed documentation on the Docker setup.

## Usage

```python
from codekg.core import CodeKnowledgeGraph
from codekg.parsers import JavaParser, PythonParser

# Initialize a new knowledge graph
ckg = CodeKnowledgeGraph()

# Parse Java code
java_parser = JavaParser()
java_parser.parse_directory("/path/to/java/code", ckg)

# Or parse Python code
python_parser = PythonParser()
python_parser.parse_directory("/path/to/python/code", ckg)

# Run queries
results = ckg.query("MATCH (c:Callable)-[:CALLS]->(d:Callable) RETURN c.name, d.name")
```

## Command-line Interface

CodeKG comes with a CLI for easy usage:

```bash
# Parse a Java codebase
python -m codekg.cli parse /path/to/java/code --language java

# Parse a Python codebase
python -m codekg.cli parse /path/to/python/code --language python

# Run analysis on parsed code
python -m codekg.cli analyze

# Run a custom Cypher query
python -m codekg.cli query "MATCH (n:Callable) RETURN n.name LIMIT 10"
```

## Implementation Details

CodeKG uses Tree-sitter for fast and accurate syntax parsing:

- Java parsing is powered by `tree-sitter-java`
- Python parsing is powered by `tree-sitter-python`

This implementation ensures better portability as it doesn't require manual compilation of language grammars.

## License

MIT 