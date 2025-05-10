# Java Code Analysis Examples

This file contains Java-specific Cypher queries and use cases for analyzing Java codebases with CodeKG.

## Setup

First, parse your Java code into the knowledge graph:

```python
from codekg.core import CodeKnowledgeGraph
from codekg.parsers import JavaParser

# Initialize graph
ckg = CodeKnowledgeGraph()

# Parse Java code
parser = JavaParser()
parser.parse_directory("/path/to/java/code", ckg)
```

## Java-Specific Use Cases

### Find All Package Declarations

```cypher
MATCH (f:File)-[:CONTAINS]->(n:Namespace)
RETURN f.path AS file, n.qualified_name AS package
```

### Find All Interfaces and Implementing Classes

```cypher
MATCH (i:Structure)<-[:IMPLEMENTS]-(c:Structure)
RETURN i.qualified_name AS interface, collect(c.qualified_name) AS implementing_classes
```

### Find All Abstract Classes and Concrete Implementations

```cypher
MATCH (a:Structure)<-[:INHERITS_FROM]-(c:Structure)
WHERE a.qualified_name STARTS WITH 'Abstract'
RETURN a.qualified_name AS abstract_class, collect(c.qualified_name) AS concrete_implementations
```

### Find Usage of Annotations

```cypher
MATCH (n)-[:ANNOTATED_BY]->(a:Annotation)
WHERE a.qualified_name STARTS WITH '@'
RETURN n.qualified_name AS element, a.qualified_name AS annotation
ORDER BY annotation, element
```

### Find Exception Handling

```cypher
MATCH (f:Callable)-[:THROWS]->(e:Structure)
RETURN f.qualified_name AS method, collect(e.qualified_name) AS exceptions
```

### Find Method Overloading

```cypher
MATCH (c:Structure)-[:CONTAINS]->(m1:Callable)
MATCH (c)-[:CONTAINS]->(m2:Callable)
WHERE m1.qualified_name CONTAINS '.' AND
      m2.qualified_name CONTAINS '.' AND
      SPLIT(m1.qualified_name, '.')[-1] = SPLIT(m2.qualified_name, '.')[-1] AND
      ID(m1) < ID(m2)  // To avoid duplicate results
RETURN c.qualified_name AS class,
       SPLIT(m1.qualified_name, '.')[-1] AS method_name,
       count(*) + 1 AS overload_count
```

## Advanced Java Analysis

### Find Classes with Many Methods (God Class Anti-pattern)

```cypher
MATCH (c:Structure)-[:CONTAINS]->(m:Callable)
WITH c, COUNT(m) AS method_count
WHERE method_count > 20
RETURN c.qualified_name AS potential_god_class, method_count
ORDER BY method_count DESC
```

### Detect Long Parameter Lists (Code Smell)

```cypher
MATCH (m:Callable)-[:HAS_PARAMETER]->(p:Parameter)
WITH m, COUNT(p) AS param_count
WHERE param_count > 5
RETURN m.qualified_name AS method, param_count
ORDER BY param_count DESC
```

### Find High Coupling Between Classes

```cypher
MATCH (c1:Structure)-[:CONTAINS]->(m:Callable),
      (m)-[:CALLS|ACCESSES|CREATES_INSTANCE]->(element)<-[:CONTAINS]-(c2:Structure)
WHERE c1 <> c2
WITH c1, c2, COUNT(*) AS coupling_count
WHERE coupling_count > 5
RETURN c1.qualified_name AS class1, c2.qualified_name AS class2, coupling_count
ORDER BY coupling_count DESC
```

### Identify Fragile Base Classes

Find parent classes with many subclasses (potential fragile base class):

```cypher
MATCH (base:Structure)<-[:INHERITS_FROM]-(derived:Structure)
WITH base, COUNT(derived) AS subclass_count
WHERE subclass_count > 5
RETURN base.qualified_name AS base_class, subclass_count
ORDER BY subclass_count DESC
```

### Detect Law of Demeter Violations

Find methods that access objects through another object (chain calls):

```cypher
MATCH (c:Structure)-[:CONTAINS]->(m:Callable)-[:CALLS]->(m1:Callable)-[:CALLS]->(m2:Callable)
WHERE NOT (m)-[:CALLS]->(m2)
RETURN m.qualified_name AS method, m1.qualified_name AS intermediate, m2.qualified_name AS target
```

## Design Pattern Detection

### Singleton Pattern Detection

```cypher
MATCH (c:Structure)-[:CONTAINS]->(m:Callable)
WHERE m.qualified_name ENDS WITH '.getInstance'
RETURN c.qualified_name AS potential_singleton, m.qualified_name AS factory_method
```

### Builder Pattern Detection

```cypher
MATCH (c:Structure)-[:CONTAINS]->(m:Callable)
WHERE m.qualified_name ENDS WITH '.build' OR m.qualified_name CONTAINS 'Builder'
RETURN c.qualified_name AS potential_builder
```

### Factory Method Pattern Detection

```cypher
MATCH (c:Structure)-[:CONTAINS]->(m:Callable),
      (m)-[:CREATES_INSTANCE]->(product:Structure)
WHERE NOT (c)-[:INHERITS_FROM]->(product) AND
      m.qualified_name CONTAINS 'create' OR m.qualified_name CONTAINS 'factory'
RETURN c.qualified_name AS factory, m.qualified_name AS factory_method, 
       product.qualified_name AS product
```

### Strategy Pattern Detection

```cypher
MATCH (context:Structure)-[:CONTAINS]->(method:Callable),
      (strategy:Structure)<-[:IMPLEMENTS]-(concrete:Structure),
      (method)-[:CALLS]->(strategyMethod:Callable)<-[:CONTAINS]-(strategy)
RETURN context.qualified_name AS context_class,
       method.qualified_name AS context_method,
       strategy.qualified_name AS strategy_interface,
       collect(concrete.qualified_name) AS concrete_strategies
``` 