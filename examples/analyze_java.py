#!/usr/bin/env python3
"""
Example script demonstrating how to use CodeKG to analyze Java code.
"""
import os
import sys
import logging
from pathlib import Path
from rich.console import Console
from rich.table import Table

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from codekg.core import CodeKnowledgeGraph
from codekg.parsers import JavaParser
from codekg.analysis import CodeMetrics


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
console = Console()


def main():
    """Main function for the example."""
    # Check if path argument is provided
    if len(sys.argv) < 2:
        console.print("[red]Error: Please provide a path to a Java project to analyze.[/red]")
        console.print("Usage: python analyze_java.py <path_to_java_project>")
        return 1
        
    java_project_path = sys.argv[1]
    
    # Create a new knowledge graph
    graph = CodeKnowledgeGraph()
    
    # Create a Java parser
    parser = JavaParser()
    
    # Parse Java code
    console.print(f"[bold cyan]Parsing Java code from {java_project_path}...[/bold cyan]")
    
    try:
        # Check if the path is a directory or file
        if os.path.isdir(java_project_path):
            parser.parse_directory(java_project_path, graph, file_extensions=['.java'])
        else:
            parser.parse_file(java_project_path, graph)
    except Exception as e:
        console.print(f"[red]Error parsing Java code: {e}[/red]")
        return 1
    
    # Print statistics
    stats = graph.get_statistics()
    
    entity_table = Table(title="Entity Statistics")
    entity_table.add_column("Entity Type", style="cyan")
    entity_table.add_column("Count", style="green")
    
    for entity_type, count in stats["entity_counts"].items():
        entity_table.add_row(entity_type, str(count))
    
    rel_table = Table(title="Relationship Statistics")
    rel_table.add_column("Relationship Type", style="cyan")
    rel_table.add_column("Count", style="green")
    
    for rel_type, count in stats["relationship_counts"].items():
        rel_table.add_row(rel_type, str(count))
    
    console.print(entity_table)
    console.print(rel_table)
    
    # Print some example queries
    console.print("\n[bold cyan]Example Queries:[/bold cyan]")
    
    # Find all classes
    classes = [entity for entity in graph.entities.values() 
              if hasattr(entity, "is_interface") and not getattr(entity, "is_interface", False)]
    
    console.print(f"[cyan]Number of classes:[/cyan] {len(classes)}")
    
    # Find all interfaces
    interfaces = [entity for entity in graph.entities.values() 
                 if hasattr(entity, "is_interface") and getattr(entity, "is_interface", True)]
    
    console.print(f"[cyan]Number of interfaces:[/cyan] {len(interfaces)}")
    
    # Find methods with parameters
    has_param_rels = [rel for rel in graph.relationships if rel.type == "HAS_PARAMETER"]
    methods_with_params = set(rel.source for rel in has_param_rels)
    
    console.print(f"[cyan]Methods with parameters:[/cyan] {len(methods_with_params)}")
    
    # Number of inheritance relationships
    inheritance_rels = [rel for rel in graph.relationships if rel.type == "INHERITS_FROM"]
    console.print(f"[cyan]Inheritance relationships:[/cyan] {len(inheritance_rels)}")
    
    # Check if we should save the graph to the database
    save_to_db = input("\nSave knowledge graph to database? (y/n): ").lower() == 'y'
    
    if save_to_db:
        try:
            console.print("[cyan]Saving to Memgraph database...[/cyan]")
            graph.save_to_db()
            console.print("[green]Knowledge graph saved to database successfully.[/green]")
            
            console.print("\n[bold cyan]To query the graph in Memgraph, use the following sample queries:[/bold cyan]")
            console.print("1. Find all classes:\n   [green]MATCH (c:Structure) WHERE NOT c.is_interface RETURN c.name, c.qualified_name[/green]")
            console.print("2. Find methods with most parameters:\n   [green]MATCH (c:Callable)-[r:HAS_PARAMETER]->(p:Parameter) RETURN c.qualified_name, count(p) AS param_count ORDER BY param_count DESC LIMIT 10[/green]")
            console.print("3. Find inheritance hierarchy:\n   [green]MATCH path = (c:Structure)-[:INHERITS_FROM*]->(super:Structure) RETURN path LIMIT 100[/green]")
            
        except Exception as e:
            console.print(f"[red]Error saving to database: {e}[/red]")
            return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 