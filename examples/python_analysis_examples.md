# Python Code Analysis Examples

This file contains Python-specific Cypher queries and use cases for analyzing Python codebases with CodeKG.

## Setup

First, parse your Python code into the knowledge graph:

```python
from codekg.core import CodeKnowledgeGraph
from codekg.parsers import PythonParser

# Initialize graph
ckg = CodeKnowledgeGraph()

# Parse Python code
parser = PythonParser()
parser.parse_directory("/path/to/python/code", ckg)
```

## Python-Specific Use Cases

### Find All Import Statements

```cypher
MATCH (f:File)-[:IMPORTS]->(i)
RETURN f.path AS file, i.qualified_name AS imported
```

### Find Usage of Decorators

```cypher
MATCH (f:Callable)-[:ANNOTATED_BY]->(d:Annotation)
WHERE d.qualified_name STARTS WITH '@'
RETURN f.qualified_name AS function, d.qualified_name AS decorator
```

### Find All Classes Inheriting from a Specific Base Class

```cypher
MATCH (c:Structure)-[:INHERITS_FROM]->(base:Structure {qualified_name: 'BaseClassName'})
RETURN c.qualified_name AS derived_class
```

### Find Type Hints Usage

```cypher
MATCH (n)-[:ANNOTATED_BY]->(t:Annotation)
WHERE NOT t.qualified_name STARTS WITH '@'  // Filter out decorators
RETURN n.qualified_name AS element, t.qualified_name AS type_hint
```

### Find Use of Magic Methods

```cypher
MATCH (c:Structure)-[:CONTAINS]->(m:Callable)
WHERE m.qualified_name CONTAINS '__' AND NOT m.qualified_name ENDS WITH '__pycache__'
RETURN c.qualified_name AS class, m.qualified_name AS magic_method
```

### Find Exception Handling

```cypher
MATCH (f:Callable)-[:THROWS]->(e:Structure)
RETURN f.qualified_name AS function, e.qualified_name AS exception
```

## Advanced Python Analysis

### Identify Dependency Structure

Find modules with many imports (potential god modules):

```cypher
MATCH (f:File)-[:IMPORTS]->(i)
WITH f, COUNT(i) AS import_count
WHERE import_count > 10
RETURN f.path AS file, import_count
ORDER BY import_count DESC
```

### Analyze Inheritance Complexity

Find classes with deep inheritance hierarchies:

```cypher
MATCH path = (c:Structure)-[:INHERITS_FROM*]->(base:Structure)
WITH c, COUNT(path) AS inheritance_depth
WHERE inheritance_depth > 2
RETURN c.qualified_name AS class, inheritance_depth
ORDER BY inheritance_depth DESC
```

### Find Commonly Used External Libraries

```cypher
MATCH (f:File)-[:IMPORTS]->(lib)
WHERE lib.qualified_name CONTAINS '.'
WITH SPLIT(lib.qualified_name, '.')[0] AS base_library, COUNT(*) AS usage_count
RETURN base_library, usage_count
ORDER BY usage_count DESC
LIMIT 10
```

### Detect Potential Circular Imports

```cypher
MATCH (f1:File)-[:IMPORTS]->(f2:File)-[:IMPORTS*]->(f1)
RETURN f1.path AS file1, f2.path AS file2
```

### Find Files with Mixed Responsibilities

Look for files that define both many classes and functions:

```cypher
MATCH (f:File)-[:CONTAINS]->(c:Structure)
WITH f, COUNT(c) AS class_count
MATCH (f)-[:CONTAINS]->(func:Callable)
WHERE NOT (func)<-[:CONTAINS]-(:Structure)  // Not a method
WITH f, class_count, COUNT(func) AS function_count
WHERE class_count > 2 AND function_count > 5
RETURN f.path AS file, class_count, function_count
```

## Pattern Detection

### Singleton Pattern Detection

```cypher
MATCH (c:Structure)-[:CONTAINS]->(constructor:Callable)
WHERE constructor.qualified_name ENDS WITH '.__init__'
MATCH (c)-[:CONTAINS]->(m:Callable)
WHERE m.qualified_name CONTAINS '__new__'
RETURN c.qualified_name AS potential_singleton
```

### Factory Method Pattern Detection

```cypher
MATCH (c:Structure)-[:CONTAINS]->(m:Callable)
MATCH (m)-[:CREATES_INSTANCE]->(product:Structure)
WHERE NOT (c)-[:INHERITS_FROM]->(product)
RETURN c.qualified_name AS factory, m.qualified_name AS factory_method, 
       product.qualified_name AS product
``` 