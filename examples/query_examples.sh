#!/bin/bash
# Examples of running Cypher queries using the CodeKG CLI

# Basic usage - get all files
echo "Running: Get all files in the codebase"
python -m codekg.cli query "MATCH (f:File) RETURN f.path LIMIT 10"

# Find function calls
echo "Running: Find function calls"
python -m codekg.cli query "MATCH (caller:Callable)-[:CALLS]->(callee:Callable) RETURN caller.qualified_name, callee.qualified_name LIMIT 10"

# Find most called functions
echo "Running: Find most called functions"
python -m codekg.cli query "MATCH (caller:Callable)-[:CALLS]->(callee:Callable) RETURN callee.qualified_name, count(*) AS times_called ORDER BY times_called DESC LIMIT 5"

# Find classes and their methods
echo "Running: Find classes and their methods"
python -m codekg.cli query "MATCH (c:Structure)-[:CONTAINS]->(m:Callable) RETURN c.qualified_name AS class, collect(m.qualified_name) AS methods LIMIT 5"

# Find inheritance relationships
echo "Running: Find inheritance relationships"
python -m codekg.cli query "MATCH (c:Structure)-[:INHERITS_FROM]->(parent:Structure) RETURN c.qualified_name AS class, parent.qualified_name AS parent_class LIMIT 10"

# Find Python decorators
echo "Running: Find Python decorators (Python only)"
python -m codekg.cli query "MATCH (f:Callable)-[:ANNOTATED_BY]->(d:Annotation) WHERE d.qualified_name STARTS WITH '@' RETURN f.qualified_name, d.qualified_name LIMIT 10"

# Find complex functions (many parameters)
echo "Running: Find functions with many parameters"
python -m codekg.cli query "MATCH (f:Callable)-[:HAS_PARAMETER]->(p:Parameter) WITH f, count(p) AS param_count WHERE param_count > 3 RETURN f.qualified_name, param_count ORDER BY param_count DESC LIMIT 5"

# Find potential Java singletons
echo "Running: Find potential Java singletons (Java only)"
python -m codekg.cli query "MATCH (c:Structure)-[:CONTAINS]->(m:Callable) WHERE m.qualified_name ENDS WITH '.getInstance' RETURN c.qualified_name, m.qualified_name LIMIT 5"

# Find all imports in a specific file
echo "Running: Find all imports in a specific file"
python -m codekg.cli query "MATCH (f:File {path: 'path/to/your/file.py'})-[:IMPORTS]->(i) RETURN i.qualified_name"

# Find files with direct dependencies on a specific file
echo "Running: Find files with direct dependencies on a specific file"
python -m codekg.cli query "MATCH (f:File)-[:IMPORTS]->(target:File {path: 'path/to/target/file.py'}) RETURN f.path"

# Advanced: Find common calling patterns
echo "Running: Find common calling patterns"
python -m codekg.cli query "MATCH (f:Callable)-[:CALLS]->(callee:Callable) WITH f, collect(callee.qualified_name) AS call_pattern WITH call_pattern, collect(f.qualified_name) AS functions_with_pattern WHERE size(functions_with_pattern) > 1 RETURN call_pattern, functions_with_pattern ORDER BY size(functions_with_pattern) DESC LIMIT 3" 