"""
Code metrics analyzer for the Code Knowledge Graph.
"""
from typing import Dict, List, Optional, Any
import logging
from collections import defaultdict

from codekg.core import CodeKnowledgeGraph


class CodeMetrics:
    """
    Analyzer for calculating code metrics from the knowledge graph.
    """
    
    def __init__(self, graph: CodeKnowledgeGraph):
        """
        Initialize the code metrics analyzer.
        
        Args:
            graph: The code knowledge graph to analyze
        """
        self.graph = graph
        self.logger = logging.getLogger(__name__)
    
    def get_complexity_metrics(self) -> Dict[str, Any]:
        """
        Calculate complexity metrics for the codebase.
        
        Returns:
            Dictionary with various complexity metrics
        """
        if self.graph.storage and self.graph.storage.is_connected:
            return self._get_complexity_metrics_from_db()
        return self._get_complexity_metrics_from_graph()
    
    def _get_complexity_metrics_from_db(self) -> Dict[str, Any]:
        """Calculate complexity metrics from the database."""
        metrics = {}
        
        # Average cyclomatic complexity
        avg_complexity_query = """
        MATCH (c:Callable)
        WHERE c.cyclomatic_complexity IS NOT NULL
        RETURN 
            avg(c.cyclomatic_complexity) AS avg_complexity,
            max(c.cyclomatic_complexity) AS max_complexity,
            count(c) AS total_callables
        """
        
        complexity_results = self.graph.query(avg_complexity_query)
        if complexity_results:
            metrics["avg_cyclomatic_complexity"] = complexity_results[0]["avg_complexity"]
            metrics["max_cyclomatic_complexity"] = complexity_results[0]["max_complexity"]
            metrics["total_callables"] = complexity_results[0]["total_callables"]
        
        # Methods per class
        methods_per_class_query = """
        MATCH (s:Structure)-[:CONTAINS]->(c:Callable)
        RETURN 
            s.qualified_name AS class_name,
            count(c) AS method_count
        ORDER BY method_count DESC
        LIMIT 10
        """
        
        methods_results = self.graph.query(methods_per_class_query)
        metrics["classes_by_method_count"] = methods_results
        
        # Calculate average methods per class
        avg_methods_query = """
        MATCH (s:Structure)
        OPTIONAL MATCH (s)-[:CONTAINS]->(c:Callable)
        WITH s, count(c) AS method_count
        RETURN avg(method_count) AS avg_methods_per_class
        """
        
        avg_methods_results = self.graph.query(avg_methods_query)
        if avg_methods_results:
            metrics["avg_methods_per_class"] = avg_methods_results[0]["avg_methods_per_class"]
        
        return metrics
    
    def _get_complexity_metrics_from_graph(self) -> Dict[str, Any]:
        """Calculate complexity metrics from the in-memory graph."""
        metrics = {}
        
        # Count callables with complexity
        callables_with_complexity = [
            c for c in self.graph.entities.values() 
            if hasattr(c, "cyclomatic_complexity") and c.cyclomatic_complexity is not None
        ]
        
        if callables_with_complexity:
            # Calculate average and max complexity
            complexities = [c.cyclomatic_complexity for c in callables_with_complexity]
            metrics["avg_cyclomatic_complexity"] = sum(complexities) / len(complexities)
            metrics["max_cyclomatic_complexity"] = max(complexities)
            metrics["total_callables"] = len(callables_with_complexity)
        
        # Methods per class
        structure_to_callables = defaultdict(list)
        for rel in self.graph.relationships:
            if rel.type == "CONTAINS":
                source_entity = self.graph.entities.get(rel.source)
                target_entity = self.graph.entities.get(rel.target)
                
                if (source_entity and target_entity and 
                    hasattr(source_entity, "is_interface") and
                    hasattr(target_entity, "__class__.__name__") and
                    target_entity.__class__.__name__ == "Callable"):
                    structure_to_callables[source_entity.qualified_name].append(target_entity)
        
        # Sort by method count
        class_method_counts = [
            {"class_name": class_name, "method_count": len(methods)}
            for class_name, methods in structure_to_callables.items()
        ]
        class_method_counts.sort(key=lambda x: x["method_count"], reverse=True)
        
        metrics["classes_by_method_count"] = class_method_counts[:10]
        
        # Calculate average methods per class
        if structure_to_callables:
            avg_methods = sum(len(methods) for methods in structure_to_callables.values()) / len(structure_to_callables)
            metrics["avg_methods_per_class"] = avg_methods
        
        return metrics
    
    def get_dependency_metrics(self) -> Dict[str, Any]:
        """
        Calculate dependency metrics for the codebase.
        
        Returns:
            Dictionary with various dependency metrics
        """
        if self.graph.storage and self.graph.storage.is_connected:
            return self._get_dependency_metrics_from_db()
        return self._get_dependency_metrics_from_graph()
    
    def _get_dependency_metrics_from_db(self) -> Dict[str, Any]:
        """Calculate dependency metrics from the database."""
        metrics = {}
        
        # Most depended-upon classes (incoming references)
        most_depended_query = """
        MATCH (s:Structure)<-[r:REFERENCES]-(c:Callable)
        RETURN
            s.qualified_name AS class_name,
            count(DISTINCT c) AS incoming_references
        ORDER BY incoming_references DESC
        LIMIT 10
        """
        
        most_depended_results = self.graph.query(most_depended_query)
        metrics["most_referenced_classes"] = most_depended_results
        
        # Classes with most outgoing dependencies
        most_dependencies_query = """
        MATCH (s:Structure)-[:CONTAINS]->(c:Callable)-[r:REFERENCES]->(target:Structure)
        WHERE s <> target
        RETURN
            s.qualified_name AS class_name,
            count(DISTINCT target) AS outgoing_references
        ORDER BY outgoing_references DESC
        LIMIT 10
        """
        
        most_dependencies_results = self.graph.query(most_dependencies_query)
        metrics["classes_with_most_dependencies"] = most_dependencies_results
        
        # Circular dependencies
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
        
        circular_deps_results = self.graph.query(circular_deps_query)
        metrics["circular_dependencies"] = circular_deps_results
        
        return metrics
    
    def _get_dependency_metrics_from_graph(self) -> Dict[str, Any]:
        """Calculate dependency metrics from the in-memory graph."""
        # Implementation would build a dependency graph from the in-memory relationships
        # and calculate metrics similar to the database queries
        return {"note": "In-memory implementation not yet available"}
    
    def get_code_organization_metrics(self) -> Dict[str, Any]:
        """
        Calculate metrics related to code organization.
        
        Returns:
            Dictionary with code organization metrics
        """
        if self.graph.storage and self.graph.storage.is_connected:
            return self._get_code_organization_metrics_from_db()
        return self._get_code_organization_metrics_from_graph()
    
    def _get_code_organization_metrics_from_db(self) -> Dict[str, Any]:
        """Calculate code organization metrics from the database."""
        metrics = {}
        
        # Package metrics
        package_metrics_query = """
        MATCH (p:Namespace)
        OPTIONAL MATCH (p)-[:CONTAINS]->(s:Structure)
        RETURN 
            p.qualified_name AS package_name,
            count(s) AS class_count
        ORDER BY class_count DESC
        LIMIT 10
        """
        
        package_results = self.graph.query(package_metrics_query)
        metrics["largest_packages"] = package_results
        
        # Inheritance depth
        inheritance_depth_query = """
        MATCH path = (s:Structure)-[:INHERITS_FROM*]->(base:Structure)
        OPTIONAL MATCH (base)-[:INHERITS_FROM]->(parent)
        WITH s, base, path, parent
        WHERE parent IS NULL
        RETURN 
            s.qualified_name AS class_name,
            base.qualified_name AS base_class,
            length(path) AS inheritance_depth
        ORDER BY inheritance_depth DESC
        LIMIT 10
        """
        
        inheritance_results = self.graph.query(inheritance_depth_query)
        metrics["deepest_inheritance_chains"] = inheritance_results
        
        return metrics
    
    def _get_code_organization_metrics_from_graph(self) -> Dict[str, Any]:
        """Calculate code organization metrics from the in-memory graph."""
        # Implementation would analyze the in-memory graph structure
        return {"note": "In-memory implementation not yet available"} 