"""
Impact analyzer for the Code Knowledge Graph.
"""
from typing import Dict, List, Optional, Any, Set
import logging
from collections import defaultdict

from codekg.core import CodeKnowledgeGraph
from codekg.graph import MemgraphClient


class ImpactAnalyzer:
    """
    Analyzer for determining the impact of changes in the codebase.
    """
    
    def __init__(self, graph: Optional[CodeKnowledgeGraph] = None, 
                client: Optional[MemgraphClient] = None):
        """
        Initialize the impact analyzer.
        
        Args:
            graph: Optional in-memory graph to analyze
            client: Optional MemgraphClient for direct database queries
        """
        self.graph = graph
        self.client = client
        self.logger = logging.getLogger(__name__)
        
        if not graph and not client:
            raise ValueError("Either graph or client must be provided")
    
    def find_affected_by_class_change(self, class_name: str) -> Dict[str, Any]:
        """
        Determine the impact of changing a class.
        
        Args:
            class_name: The qualified name of the class being changed
            
        Returns:
            Dictionary with impact analysis results
        """
        if self.client:
            return self._find_affected_by_class_change_from_db(class_name)
        return self._find_affected_by_class_change_from_graph(class_name)
    
    def _find_affected_by_class_change_from_db(self, class_name: str) -> Dict[str, Any]:
        """Find affected components using database queries."""
        results = {
            "class_name": class_name,
            "affected_classes": [],
            "affected_methods": [],
            "affected_by_inheritance": [],
            "total_affected_count": 0
        }
        
        # Find classes that reference this class
        references_query = """
        MATCH (s:Structure)-[:CONTAINS]->(c:Callable)-[:REFERENCES]->(target:Structure)
        WHERE target.qualified_name = $class_name AND s.qualified_name <> $class_name
        RETURN DISTINCT
            s.qualified_name AS affected_class,
            collect(c.qualified_name) AS affected_methods
        """
        
        references_results = self.client.execute_query(references_query, {'class_name': class_name})
        
        for result in references_results:
            results["affected_classes"].append({
                "class_name": result["affected_class"],
                "reason": "REFERENCES"
            })
            
            for method in result["affected_methods"]:
                results["affected_methods"].append({
                    "method_name": method,
                    "reason": "REFERENCES"
                })
        
        # Find classes that inherit from this class
        inherits_query = """
        MATCH (s:Structure)-[:INHERITS_FROM]->(target:Structure)
        WHERE target.qualified_name = $class_name
        RETURN
            s.qualified_name AS affected_class
        """
        
        inherits_results = self.client.execute_query(inherits_query, {'class_name': class_name})
        
        for result in inherits_results:
            results["affected_classes"].append({
                "class_name": result["affected_class"],
                "reason": "INHERITS_FROM"
            })
            results["affected_by_inheritance"].append(result["affected_class"])
        
        # Find classes that implement this interface (if it's an interface)
        implements_query = """
        MATCH (s:Structure)-[:IMPLEMENTS]->(target:Structure)
        WHERE target.qualified_name = $class_name
        RETURN
            s.qualified_name AS affected_class
        """
        
        implements_results = self.client.execute_query(implements_query, {'class_name': class_name})
        
        for result in implements_results:
            results["affected_classes"].append({
                "class_name": result["affected_class"],
                "reason": "IMPLEMENTS"
            })
            results["affected_by_inheritance"].append(result["affected_class"])
        
        # Calculate total affected
        results["total_affected_count"] = len(results["affected_classes"])
        
        return results
    
    def _find_affected_by_class_change_from_graph(self, class_name: str) -> Dict[str, Any]:
        """Find affected components using in-memory graph traversal."""
        results = {
            "class_name": class_name,
            "affected_classes": [],
            "affected_methods": [],
            "affected_by_inheritance": [],
            "total_affected_count": 0
        }
        
        # First find the class entity
        class_entity = None
        for entity in self.graph.entities.values():
            if (hasattr(entity, "qualified_name") and 
                entity.qualified_name == class_name and
                hasattr(entity, "is_interface")):
                class_entity = entity
                break
                
        if not class_entity:
            self.logger.warning(f"Class {class_name} not found in graph")
            return results
            
        # Find classes that reference this class
        for rel in self.graph.relationships:
            if rel.type == "REFERENCES" and rel.target == class_entity.id:
                source_entity = self.graph.entities.get(rel.source)
                
                if source_entity and source_entity.__class__.__name__ == "Callable":
                    # Find which class this callable belongs to
                    for contain_rel in self.graph.relationships:
                        if (contain_rel.type == "CONTAINS" and
                            contain_rel.target == source_entity.id):
                            
                            container_entity = self.graph.entities.get(contain_rel.source)
                            if (container_entity and 
                                hasattr(container_entity, "is_interface") and
                                container_entity.id != class_entity.id):
                                
                                results["affected_classes"].append({
                                    "class_name": container_entity.qualified_name,
                                    "reason": "REFERENCES"
                                })
                                
                                results["affected_methods"].append({
                                    "method_name": source_entity.qualified_name,
                                    "reason": "REFERENCES"
                                })
        
        # Find classes that inherit from this class
        for rel in self.graph.relationships:
            if rel.type == "INHERITS_FROM" and rel.target == class_entity.id:
                source_entity = self.graph.entities.get(rel.source)
                if source_entity:
                    results["affected_classes"].append({
                        "class_name": source_entity.qualified_name,
                        "reason": "INHERITS_FROM"
                    })
                    results["affected_by_inheritance"].append(source_entity.qualified_name)
        
        # Find classes that implement this interface
        for rel in self.graph.relationships:
            if rel.type == "IMPLEMENTS" and rel.target == class_entity.id:
                source_entity = self.graph.entities.get(rel.source)
                if source_entity:
                    results["affected_classes"].append({
                        "class_name": source_entity.qualified_name,
                        "reason": "IMPLEMENTS"
                    })
                    results["affected_by_inheritance"].append(source_entity.qualified_name)
        
        # Remove duplicates
        results["affected_classes"] = [dict(t) for t in {tuple(d.items()) for d in results["affected_classes"]}]
        results["affected_methods"] = [dict(t) for t in {tuple(d.items()) for d in results["affected_methods"]}]
        results["affected_by_inheritance"] = list(set(results["affected_by_inheritance"]))
        
        # Calculate total affected
        results["total_affected_count"] = len(results["affected_classes"])
        
        return results
    
    def find_affected_by_method_change(self, method_qualified_name: str) -> Dict[str, Any]:
        """
        Determine the impact of changing a method.
        
        Args:
            method_qualified_name: The qualified name of the method being changed
            
        Returns:
            Dictionary with impact analysis results
        """
        if self.client:
            return self._find_affected_by_method_change_from_db(method_qualified_name)
        return self._find_affected_by_method_change_from_graph(method_qualified_name)
    
    def _find_affected_by_method_change_from_db(self, method_qualified_name: str) -> Dict[str, Any]:
        """Find methods affected by a method change using database queries."""
        results = {
            "method_name": method_qualified_name,
            "callers": [],
            "overriding_methods": [],
            "overridden_methods": [],
            "total_affected_count": 0
        }
        
        # Find methods that call this method
        calls_query = """
        MATCH (caller:Callable)-[:CALLS]->(target:Callable)
        WHERE target.qualified_name = $method_name
        RETURN DISTINCT
            caller.qualified_name AS caller_method
        """
        
        calls_results = self.client.execute_query(calls_query, {'method_name': method_qualified_name})
        
        for result in calls_results:
            results["callers"].append(result["caller_method"])
        
        # Find methods that override this method (if it's in a superclass)
        overrides_query = """
        MATCH (m:Callable)<-[:OVERRIDES]-(override:Callable)
        WHERE m.qualified_name = $method_name
        RETURN DISTINCT
            override.qualified_name AS overriding_method
        """
        
        overrides_results = self.client.execute_query(overrides_query, 
                                                   {'method_name': method_qualified_name})
        
        for result in overrides_results:
            results["overriding_methods"].append(result["overriding_method"])
        
        # Find methods that this method overrides
        overridden_query = """
        MATCH (m:Callable)-[:OVERRIDES]->(overridden:Callable)
        WHERE m.qualified_name = $method_name
        RETURN DISTINCT
            overridden.qualified_name AS overridden_method
        """
        
        overridden_results = self.client.execute_query(overridden_query, 
                                                    {'method_name': method_qualified_name})
        
        for result in overridden_results:
            results["overridden_methods"].append(result["overridden_method"])
        
        # Calculate total affected
        results["total_affected_count"] = (len(results["callers"]) + 
                                         len(results["overriding_methods"]))
        
        return results
    
    def _find_affected_by_method_change_from_graph(self, method_qualified_name: str) -> Dict[str, Any]:
        """Find methods affected by a method change using in-memory graph traversal."""
        results = {
            "method_name": method_qualified_name,
            "callers": [],
            "overriding_methods": [],
            "overridden_methods": [],
            "total_affected_count": 0
        }
        
        # Find the method entity
        method_entity = None
        for entity in self.graph.entities.values():
            if (hasattr(entity, "qualified_name") and 
                entity.qualified_name == method_qualified_name and
                entity.__class__.__name__ == "Callable"):
                method_entity = entity
                break
                
        if not method_entity:
            self.logger.warning(f"Method {method_qualified_name} not found in graph")
            return results
            
        # Find methods that call this method
        for rel in self.graph.relationships:
            if rel.type == "CALLS" and rel.target == method_entity.id:
                caller_entity = self.graph.entities.get(rel.source)
                if caller_entity:
                    results["callers"].append(caller_entity.qualified_name)
        
        # Find methods that override this method
        for rel in self.graph.relationships:
            if rel.type == "OVERRIDES" and rel.target == method_entity.id:
                override_entity = self.graph.entities.get(rel.source)
                if override_entity:
                    results["overriding_methods"].append(override_entity.qualified_name)
        
        # Find methods that this method overrides
        for rel in self.graph.relationships:
            if rel.type == "OVERRIDES" and rel.source == method_entity.id:
                overridden_entity = self.graph.entities.get(rel.target)
                if overridden_entity:
                    results["overridden_methods"].append(overridden_entity.qualified_name)
        
        # Calculate total affected
        results["total_affected_count"] = (len(results["callers"]) + 
                                         len(results["overriding_methods"]))
        
        return results
    
    def calculate_change_impact_score(self, entity_name: str) -> float:
        """
        Calculate a numerical score representing the impact of changing a code entity.
        
        Args:
            entity_name: The qualified name of the entity (class or method)
            
        Returns:
            Impact score (higher means more impact)
        """
        # Check if this is likely a class or method based on name
        is_class = "." not in entity_name or entity_name.split(".")[-1][0].isupper()
        
        if is_class:
            impact_data = self.find_affected_by_class_change(entity_name)
            direct_dependents = len(impact_data["affected_classes"])
            inheritance_dependents = len(impact_data["affected_by_inheritance"])
            
            # Classes that inherit have a higher impact multiplier
            score = direct_dependents + (inheritance_dependents * 2)
        else:
            impact_data = self.find_affected_by_method_change(entity_name)
            direct_callers = len(impact_data["callers"])
            overriding_methods = len(impact_data["overriding_methods"])
            
            # Overriding methods have a higher impact multiplier
            score = direct_callers + (overriding_methods * 1.5)
            
        return score 