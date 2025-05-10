# CodeKG Examples

This directory contains examples and use cases for the CodeKG (Code Knowledge Graph) library.

## Contents

- `analyze_python.py` - Script for analyzing Python code structure
- `analyze_java.py` - Script for analyzing Java code structure
- `cypher_queries.md` - General purpose Cypher queries for code analysis
- `python_analysis_examples.md` - Python-specific analysis queries and examples
- `java_analysis_examples.md` - Java-specific analysis queries and examples
- `query_examples.sh` - Example shell script for running queries via the CLI

## Quick Start

1. Parse your codebase into the graph database:

```bash
# For Python codebases
python -m codekg.cli parse /path/to/python/code --language python

# For Java codebases
python -m codekg.cli parse /path/to/java/code --language java
```

2. Run example queries using the shell script:

```bash
# Make sure the script is executable
chmod +x examples/query_examples.sh

# Run the example queries
./examples/query_examples.sh
```

3. Or run individual queries:

```bash
python -m codekg.cli query "MATCH (f:File) RETURN f.path LIMIT 10"
```

## Database Access

All examples assume you have access to either:

- A running instance of Memgraph (via Docker: `docker-compose -f docker/docker-compose.yaml up memgraph lab`)
- A running instance of KuzuDB (via Docker: `docker-compose -f docker/docker-compose.yaml up kuzudb-explorer`)

See the main README and the docker/README.md files for more information on setting up the databases.

## Analysis Use Cases

The examples in this directory cover various code analysis use cases, including:

- Dependency analysis (imports, module relationships)
- Call graph analysis (function calls, call hierarchies)
- Code structure analysis (classes, methods, variables)
- Complexity analysis (function size, parameter counts)
- Code quality metrics (unused code, over-complex methods)
- Design pattern detection (singletons, factories, etc.)
- Language-specific features (Python decorators, Java annotations)

For detailed queries covering each use case, see the respective markdown files. 