# Example Cypher Queries for Code Analysis

This document contains useful Cypher queries for analyzing code using CodeKG. These queries work with both Memgraph and KuzuDB graph databases.

## Basic Queries

### Count Nodes by Type

```cypher
MATCH (n)
RETURN labels(n) AS type, count(n) AS count
ORDER BY count DESC
```

### Find All Files in the Codebase

```cypher
MATCH (f:File)
RETURN f.path AS file_path
ORDER BY file_path
```

## Call Graph Analysis

### Find All Function Calls

```cypher
MATCH (caller:Callable)-[:CALLS]->(callee:Callable)
RETURN caller.qualified_name AS caller, callee.qualified_name AS callee
```

### Find Most Called Functions

```cypher
MATCH (caller:Callable)-[:CALLS]->(callee:Callable)
RETURN callee.qualified_name AS function, count(*) AS times_called
ORDER BY times_called DESC
LIMIT 10
```

### Find Recursive Functions

```cypher
MATCH (f:Callable)-[:CALLS]->(f)
RETURN f.qualified_name AS recursive_function
```

### Find Functions That Call Each Other (Cycles)

```cypher
MATCH (f1:Callable)-[:CALLS]->(f2:Callable)-[:CALLS]->(f1)
RETURN f1.qualified_name AS function1, f2.qualified_name AS function2
```

## Dependency Analysis

### Find Direct Dependencies Between Files

```cypher
MATCH (f1:File)-[:IMPORTS]->(f2:File)
RETURN f1.path AS source_file, f2.path AS imported_file
```

### Find Transitive Dependencies (Files that depend on a specific file)

```cypher
MATCH (f:File {path: 'path/to/target/file.py'})
MATCH (dependent:File)-[:IMPORTS*]->(f)
RETURN dependent.path AS dependent_file
```

## Code Structure Analysis

### Find All Classes and Their Methods

```cypher
MATCH (c:Structure)-[:CONTAINS]->(m:Callable)
RETURN c.qualified_name AS class, collect(m.qualified_name) AS methods
```

### Find Class Inheritance Hierarchy

```cypher
MATCH (c:Structure)-[:INHERITS_FROM*]->(parent:Structure)
RETURN c.qualified_name AS class, collect(parent.qualified_name) AS inheritance_chain
```

### Find Classes Implementing Interfaces

```cypher
MATCH (c:Structure)-[:IMPLEMENTS]->(i:Structure)
RETURN c.qualified_name AS class, collect(i.qualified_name) AS implemented_interfaces
```

## Complexity Analysis

### Find Functions with Many Parameters

```cypher
MATCH (f:Callable)-[:HAS_PARAMETER]->(p:Parameter)
WITH f, count(p) AS param_count
WHERE param_count > 5
RETURN f.qualified_name AS function, param_count
ORDER BY param_count DESC
```

### Find Functions That Call Many Other Functions

```cypher
MATCH (caller:Callable)-[:CALLS]->(callee:Callable)
WITH caller, count(DISTINCT callee) AS call_count
WHERE call_count > 10
RETURN caller.qualified_name AS complex_function, call_count
ORDER BY call_count DESC
```

## Code Quality Analysis

### Find Unused Functions

```cypher
MATCH (f:Callable)
WHERE NOT EXISTS { MATCH ()-[:CALLS]->(f) }
AND NOT f.qualified_name CONTAINS "__init__"
AND NOT f.qualified_name CONTAINS "main"
RETURN f.qualified_name AS unused_function
```

### Find Dead Code (Functions Not Called from Main Flow)

```cypher
MATCH (entry:Callable {qualified_name: "main"})
MATCH (f:Callable)
WHERE NOT EXISTS { 
  MATCH (entry)-[:CALLS*]->(f) 
}
AND NOT f.qualified_name = "main"
RETURN f.qualified_name AS potentially_dead_code
```

## Variable Usage Analysis

### Find All Variable Accesses in a Function

```cypher
MATCH (f:Callable {qualified_name: "target_function"})-[:ACCESSES]->(v:Variable)
RETURN v.qualified_name AS accessed_variable
```

### Find Global Variables Used Across Multiple Functions

```cypher
MATCH (f:Callable)-[:ACCESSES]->(v:Variable)
WHERE NOT (v)<-[:CONTAINS]-(:Callable)  // Not a local variable
WITH v, count(DISTINCT f) AS usage_count
WHERE usage_count > 1
RETURN v.qualified_name AS global_variable, usage_count
ORDER BY usage_count DESC
```

## Comment Analysis

### Find Functions with Associated Comments

```cypher
MATCH (f:Callable)-[:ASSOCIATED_COMMENT]->(c:Comment)
RETURN f.qualified_name AS function, c.qualified_name AS comment
```

## Type Information

### Find Type Annotations for Variables and Parameters

```cypher
MATCH (n)-[:ANNOTATED_BY]->(t:Annotation)
RETURN n.qualified_name AS element, t.qualified_name AS type
```

## Advanced Analysis

### Find Potential Bottlenecks (Functions Called by Many Others)

```cypher
MATCH (caller:Callable)-[:CALLS]->(callee:Callable)
WITH callee, count(DISTINCT caller) AS caller_count
WHERE caller_count > 5
RETURN callee.qualified_name AS potential_bottleneck, caller_count
ORDER BY caller_count DESC
```

### Find Common Patterns with Clustering

```cypher
MATCH (f:Callable)-[:CALLS]->(callee:Callable)
WITH f, collect(callee.qualified_name) AS call_pattern
WITH call_pattern, collect(f.qualified_name) AS functions_with_pattern
WHERE size(functions_with_pattern) > 1
RETURN call_pattern, functions_with_pattern
ORDER BY size(functions_with_pattern) DESC
LIMIT 10
``` 