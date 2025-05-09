"""
Dependency analyzer for the Code Knowledge Graph.
"""
from typing import Dict, List, Optional, Any
import logging
from collections import defaultdict

from codekg.core import CodeKnowledgeGraph
from codekg.graph import MemgraphClient


class DependencyAnalyzer:
    """
    Analyzer for extracting and analyzing dependencies in the code knowledge graph.
    """
    
    def __init__(self, graph: Optional[CodeKnowledgeGraph] = None, 
                client: Optional[MemgraphClient] = None):
        """
        Initialize the dependency analyzer.
        
        Args:
            graph: Optional in-memory graph to analyze
            client: Optional MemgraphClient for direct database queries
        """
        self.graph = graph
        self.client = client
        self.logger = logging.getLogger(__name__)
        
        if not graph and not client:
            raise ValueError("Either graph or client must be provided")
    
    def get_direct_dependencies(self, class_name: str) -> List[Dict[str, Any]]:
        """
        Get all direct dependencies of a class.
        
        Args:
            class_name: The qualified name of the class
            
        Returns:
            List of dependent classes with dependency type
        """
        if self.client:
            return self._get_direct_dependencies_from_db(class_name)
        return self._get_direct_dependencies_from_graph(class_name)
    
    def _get_direct_dependencies_from_db(self, class_name: str) -> List[Dict[str, Any]]:
        """Get direct dependencies from the database."""
        # Query for REFERENCES relationships
        references_query = """
        MATCH (s:Structure)-[:CONTAINS]->(c:Callable)-[r:REFERENCES]->(target:Structure)
        WHERE s.qualified_name = $class_name AND s <> target
        RETURN DISTINCT
            target.qualified_name AS dependency_name,
            'REFERENCES' AS dependency_type
        """
        
        # Query for INHERITS_FROM relationships
        inherits_query = """
        MATCH (s:Structure)-[r:INHERITS_FROM]->(target:Structure)
        WHERE s.qualified_name = $class_name
        RETURN DISTINCT
            target.qualified_name AS dependency_name,
            'INHERITS_FROM' AS dependency_type
        """
        
        # Query for IMPLEMENTS relationships
        implements_query = """
        MATCH (s:Structure)-[r:IMPLEMENTS]->(target:Structure)
        WHERE s.qualified_name = $class_name
        RETURN DISTINCT
            target.qualified_name AS dependency_name,
            'IMPLEMENTS' AS dependency_type
        """
        
        # Execute queries and combine results
        references_results = self.client.execute_query(references_query, {'class_name': class_name})
        inherits_results = self.client.execute_query(inherits_query, {'class_name': class_name})
        implements_results = self.client.execute_query(implements_query, {'class_name': class_name})
        
        all_dependencies = []
        all_dependencies.extend(references_results)
        all_dependencies.extend(inherits_results)
        all_dependencies.extend(implements_results)
        
        return all_dependencies
    
    def _get_direct_dependencies_from_graph(self, class_name: str) -> List[Dict[str, Any]]:
        """Get direct dependencies from the in-memory graph."""
        results = []
        class_entity = None
        
        # Find the class entity
        for entity in self.graph.entities.values():
            if (hasattr(entity, "qualified_name") and 
                entity.qualified_name == class_name and
                hasattr(entity, "is_interface")):
                class_entity = entity
                break
        
        if not class_entity:
            self.logger.warning(f"Class {class_name} not found in graph")
            return results
            
        # Find REFERENCES relationships
        for rel in self.graph.relationships:
            if rel.type == "REFERENCES":
                source_entity = self.graph.entities.get(rel.source)
                target_entity = self.graph.entities.get(rel.target)
                
                # Check if source is a callable within our class
                if (source_entity and target_entity and
                    source_entity.__class__.__name__ == "Callable" and
                    target_entity.__class__.__name__ == "Structure"):
                    
                    # Find if the callable belongs to our class
                    for contain_rel in self.graph.relationships:
                        if (contain_rel.type == "CONTAINS" and
                            contain_rel.source == class_entity.id and
                            contain_rel.target == source_entity.id):
                            
                            # We found a REFERENCES from our class to another Structure
                            results.append({
                                "dependency_name": target_entity.qualified_name,
                                "dependency_type": "REFERENCES"
                            })
        
        # Find INHERITS_FROM relationships
        for rel in self.graph.relationships:
            if rel.type == "INHERITS_FROM" and rel.source == class_entity.id:
                target_entity = self.graph.entities.get(rel.target)
                if target_entity:
                    results.append({
                        "dependency_name": target_entity.qualified_name,
                        "dependency_type": "INHERITS_FROM"
                    })
        
        # Find IMPLEMENTS relationships
        for rel in self.graph.relationships:
            if rel.type == "IMPLEMENTS" and rel.source == class_entity.id:
                target_entity = self.graph.entities.get(rel.target)
                if target_entity:
                    results.append({
                        "dependency_name": target_entity.qualified_name,
                        "dependency_type": "IMPLEMENTS"
                    })
        
        return results
    
    def get_dependency_graph(self, root_class: str, depth: int = 2) -> Dict[str, Any]:
        """
        Get a dependency graph starting from a root class.
        
        Args:
            root_class: The qualified name of the root class
            depth: Maximum depth of dependencies to traverse
            
        Returns:
            Dictionary representing the dependency graph
        """
        if self.client:
            return self._get_dependency_graph_from_db(root_class, depth)
        return self._get_dependency_graph_from_graph(root_class, depth)
    
    def _get_dependency_graph_from_db(self, root_class: str, depth: int) -> Dict[str, Any]:
        """Get dependency graph from the database."""
        dependency_query = """
        MATCH path = (s:Structure)-[:CONTAINS|REFERENCES|INHERITS_FROM|IMPLEMENTS*1..{depth}]->(target)
        WHERE s.qualified_name = $root_class
        RETURN 
            path, 
            length(path) AS path_length
        LIMIT 100
        """
        
        results = self.client.execute_query(dependency_query, {
            'root_class': root_class,
            'depth': depth
        })
        
        # Transform results into a more usable format
        # This would normally convert the paths into a proper graph structure
        # but is simplified here
        return {
            "root": root_class,
            "max_depth": depth,
            "paths_found": len(results)
        }
    
    def _get_dependency_graph_from_graph(self, root_class: str, depth: int) -> Dict[str, Any]:
        """Get dependency graph from the in-memory graph."""
        # This would normally build a graph by traversing relationships
        # from the root class up to the specified depth
        return {
            "root": root_class,
            "max_depth": depth,
            "note": "In-memory implementation not yet available"
        }
        
    def find_circular_dependencies(self) -> List[Dict[str, Any]]:
        """
        Find circular dependencies between classes.
        
        Returns:
            List of circular dependency chains found
        """
        if self.client:
            return self._find_circular_dependencies_from_db()
        return self._find_circular_dependencies_from_graph()
    
    def _find_circular_dependencies_from_db(self) -> List[Dict[str, Any]]:
        """Find circular dependencies from the database."""
        circular_deps_query = """
        MATCH path = (s1:Structure)-[:CONTAINS]->
                     (c1:Callable)-[:REFERENCES]->(s2:Structure)-[:CONTAINS]->
                     (c2:Callable)-[:REFERENCES]->(s1:Structure)
        WHERE s1 <> s2
        RETURN 
            s1.qualified_name AS class1,
            s2.qualified_name AS class2,
            count(path) AS reference_count
        ORDER BY reference_count DESC
        LIMIT 10
        """
        
        return self.client.execute_query(circular_deps_query)
    
    def _find_circular_dependencies_from_graph(self) -> List[Dict[str, Any]]:
        """Find circular dependencies from the in-memory graph."""
        # This would build a dependency graph and find cycles
        # Complex implementation left for the actual implementation
        return [] 