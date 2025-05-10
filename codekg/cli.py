"""
Command-line interface for CodeKG.
"""
import os
import sys
import logging
import json
from pathlib import Path
import click
from rich.console import Console
from rich.table import Table
from rich.logging import RichHandler

from codekg.core import CodeKnowledgeGraph
from codekg.parsers import JavaParser, PythonParser
from codekg.graph import MemgraphClient


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("codekg")
console = Console()


@click.group()
@click.version_option("0.1.0")
def cli():
    """CodeKG - An extensible knowledge graph framework for code."""
    pass


@cli.command()
@click.argument('source_path', type=click.Path(exists=True))
@click.option('--language', '-l', default='java', help='Source code language (java, python)')
@click.option('--db-type', default='memgraph', type=click.Choice(['memgraph', 'falkordb', 'neo4j', 'kuzudb']), 
              help='Graph database type')
@click.option('--db-host', default='localhost', help='Database server host')
@click.option('--db-port', default=None, type=int, 
              help='Database server port (default: memgraph=7687, falkordb=6379, neo4j=7687)')
@click.option('--db-user', default=None, help='Database username')
@click.option('--db-pass', default=None, help='Database password')
@click.option('--db-name', default=None, help='Database name (for Neo4j)')
@click.option('--db-path', default=None, help='Database path (for KuzuDB on-disk mode)')
@click.option('--db-in-memory', is_flag=True, help='Use in-memory mode (for KuzuDB)')
@click.option('--db-save/--no-db-save', default=True, help='Save to database after parsing')
def parse(source_path, language, db_type, db_host, db_port, db_user, db_pass, db_name, db_path, db_in_memory, db_save):
    """Parse source code and build a knowledge graph."""
    source_path = os.path.abspath(source_path)
    
    # Configure storage based on selected database type
    storage_config = {}
    
    # Handle different database types
    if db_type in ["memgraph", "falkordb", "neo4j"]:
        storage_config["host"] = db_host
        
        # Set default ports based on database type if not provided
        if db_port is None:
            if db_type == "memgraph":
                db_port = 7687
            elif db_type == "falkordb":
                db_port = 6379
            elif db_type == "neo4j":
                db_port = 7687
        
        storage_config["port"] = db_port
        
        # Add authentication if provided
        if db_user is not None:
            storage_config["username"] = db_user
        if db_pass is not None:
            storage_config["password"] = db_pass
        
        # Add database name for Neo4j
        if db_type == "neo4j" and db_name is not None:
            storage_config["database"] = db_name
    
    # Handle KuzuDB specific configuration
    elif db_type == "kuzudb":
        if db_path:
            storage_config["db_path"] = db_path
        if db_in_memory:
            storage_config["in_memory"] = True

    # Initialize the graph with the configured storage
    graph = CodeKnowledgeGraph(storage_type=db_type, storage_config=storage_config)
    
    with console.status(f"Parsing {language} code from {source_path}...", spinner="dots"):
        if language.lower() == 'java':
            parser = JavaParser()
            if os.path.isdir(source_path):
                parser.parse_directory(source_path, graph, file_extensions=['.java'])
            else:
                parser.parse_file(source_path, graph)
        elif language.lower() == 'python':
            parser = PythonParser()
            if os.path.isdir(source_path):
                parser.parse_directory(source_path, graph, file_extensions=['.py'])
            else:
                parser.parse_file(source_path, graph)
        else:
            console.print(f"[red]Error: Language '{language}' is not supported yet. Valid options: java, python[/red]")
            return
    
    # Print stats
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
    
    if db_save:
        with console.status(f"Saving to {db_type} database...", spinner="dots"):
            graph.save_to_db()
        console.print("[green]Knowledge graph saved to database successfully.[/green]")
    
    console.print(f"[green]Parsing complete. {stats['total_entities']} entities and {stats['total_relationships']} relationships extracted.[/green]")


@cli.command()
@click.option('--db-type', default='memgraph', type=click.Choice(['memgraph', 'falkordb', 'neo4j', 'kuzudb']), 
              help='Graph database type')
@click.option('--db-host', default='localhost', help='Database server host')
@click.option('--db-port', default=None, type=int, 
              help='Database server port (default: memgraph=7687, falkordb=6379, neo4j=7687)')
@click.option('--db-user', default=None, help='Database username')
@click.option('--db-pass', default=None, help='Database password')
@click.option('--db-name', default=None, help='Database name (for Neo4j)')
@click.option('--db-path', default=None, help='Database path (for KuzuDB on-disk mode)')
@click.option('--db-in-memory', is_flag=True, help='Use in-memory mode (for KuzuDB)')
@click.option('--export-dir', type=click.Path(), help='Export metrics to JSON file')
def analyze(db_type, db_host, db_port, db_user, db_pass, db_name, db_path, db_in_memory, export_dir):
    """Analyze the code knowledge graph and show metrics."""
    try:
        # Configure storage based on selected database type
        storage_config = {}
        
        # Handle different database types
        if db_type in ["memgraph", "falkordb", "neo4j"]:
            storage_config["host"] = db_host
            
            # Set default ports based on database type if not provided
            if db_port is None:
                if db_type == "memgraph":
                    db_port = 7687
                elif db_type == "falkordb":
                    db_port = 6379
                elif db_type == "neo4j":
                    db_port = 7687
            
            storage_config["port"] = db_port
            
            # Add authentication if provided
            if db_user is not None:
                storage_config["username"] = db_user
            if db_pass is not None:
                storage_config["password"] = db_pass
            
            # Add database name for Neo4j
            if db_type == "neo4j" and db_name is not None:
                storage_config["database"] = db_name
        
        # Handle KuzuDB specific configuration
        elif db_type == "kuzudb":
            if db_path:
                storage_config["db_path"] = db_path
            if db_in_memory:
                storage_config["in_memory"] = True

        # Initialize the graph with the configured storage
        graph = CodeKnowledgeGraph(storage_type=db_type, storage_config=storage_config)

        # Import required code metrics class in this function to avoid circular import
        from codekg.analysis import CodeMetrics
        metrics = CodeMetrics(graph=graph)
        
        with console.status("Calculating complexity metrics...", spinner="dots"):
            complexity_metrics = metrics.get_complexity_metrics()
        
        with console.status("Calculating dependency metrics...", spinner="dots"):
            dependency_metrics = metrics.get_dependency_metrics()
        
        with console.status("Calculating code organization metrics...", spinner="dots"):
            organization_metrics = metrics.get_code_organization_metrics()
        
        # Display metrics
        console.print("[bold cyan]Code Complexity Metrics[/bold cyan]")
        for key, value in complexity_metrics.items():
            if key != "classes_by_method_count":
                console.print(f"[cyan]{key}:[/cyan] {value}")
        
        # Display top classes by method count
        if "classes_by_method_count" in complexity_metrics:
            method_table = Table(title="Top Classes by Method Count")
            method_table.add_column("Class", style="cyan")
            method_table.add_column("Method Count", style="green")
            
            for item in complexity_metrics["classes_by_method_count"]:
                method_table.add_row(item["class_name"], str(item["method_count"]))
            
            console.print(method_table)
        
        # Display most referenced classes
        if "most_referenced_classes" in dependency_metrics:
            ref_table = Table(title="Most Referenced Classes")
            ref_table.add_column("Class", style="cyan")
            ref_table.add_column("Incoming References", style="green")
            
            for item in dependency_metrics["most_referenced_classes"]:
                ref_table.add_row(item["class_name"], str(item["incoming_references"]))
            
            console.print(ref_table)
        
        # Export metrics if requested
        if export_dir:
            all_metrics = {
                "complexity": complexity_metrics,
                "dependency": dependency_metrics,
                "organization": organization_metrics
            }
            
            os.makedirs(export_dir, exist_ok=True)
            export_path = os.path.join(export_dir, "metrics.json")
            
            with open(export_path, 'w') as f:
                json.dump(all_metrics, f, indent=2)
            
            console.print(f"[green]Metrics exported to {export_path}[/green]")
    
    except Exception as e:
        console.print(f"[red]Error analyzing code knowledge graph: {e}[/red]")


@cli.command()
@click.argument('query', type=str)
@click.option('--db-type', default='memgraph', type=click.Choice(['memgraph', 'falkordb', 'neo4j', 'kuzudb']), 
              help='Graph database type')
@click.option('--db-host', default='localhost', help='Database server host')
@click.option('--db-port', default=None, type=int, 
              help='Database server port (default: memgraph=7687, falkordb=6379, neo4j=7687)')
@click.option('--db-user', default=None, help='Database username')
@click.option('--db-pass', default=None, help='Database password')
@click.option('--db-name', default=None, help='Database name (for Neo4j)')
@click.option('--db-path', default=None, help='Database path (for KuzuDB on-disk mode)')
@click.option('--db-in-memory', is_flag=True, help='Use in-memory mode (for KuzuDB)')
@click.option('--output', '-o', type=click.Path(), help='Output results to JSON file')
def query(query, db_type, db_host, db_port, db_user, db_pass, db_name, db_path, db_in_memory, output):
    """Run a Cypher query against the knowledge graph database."""
    try:
        # Configure storage based on selected database type
        storage_config = {}
        
        # Handle different database types
        if db_type in ["memgraph", "falkordb", "neo4j"]:
            storage_config["host"] = db_host
            
            # Set default ports based on database type if not provided
            if db_port is None:
                if db_type == "memgraph":
                    db_port = 7687
                elif db_type == "falkordb":
                    db_port = 6379
                elif db_type == "neo4j":
                    db_port = 7687
            
            storage_config["port"] = db_port
            
            # Add authentication if provided
            if db_user is not None:
                storage_config["username"] = db_user
            if db_pass is not None:
                storage_config["password"] = db_pass
            
            # Add database name for Neo4j
            if db_type == "neo4j" and db_name is not None:
                storage_config["database"] = db_name
        
        # Handle KuzuDB specific configuration
        elif db_type == "kuzudb":
            if db_path:
                storage_config["db_path"] = db_path
            if db_in_memory:
                storage_config["in_memory"] = True

        # Initialize the graph with the configured storage
        graph = CodeKnowledgeGraph(storage_type=db_type, storage_config=storage_config)
        
        with console.status(f"Executing query...", spinner="dots"):
            results = graph.query(query)
        
        if not results:
            console.print("[yellow]Query returned no results.[/yellow]")
            return
        
        # Create table
        result_table = Table(title=f"Query Results ({len(results)} rows)")
        
        # Add columns based on first row
        for key in results[0].keys():
            result_table.add_column(key, style="cyan")
        
        # Add rows
        for result in results:
            values = []
            for key in results[0].keys():
                val = result.get(key, "")
                if isinstance(val, (dict, list)):
                    # Format complex objects
                    values.append(str(val))
                else:
                    values.append(str(val))
            result_table.add_row(*values)
        
        console.print(result_table)
        
        # Export if requested
        if output:
            with open(output, 'w') as f:
                json.dump(results, f, indent=2)
            console.print(f"[green]Results exported to {output}[/green]")
    
    except Exception as e:
        console.print(f"[red]Error executing query: {e}[/red]")


@cli.command()
@click.option('--db-type', default='memgraph', type=click.Choice(['memgraph', 'falkordb', 'neo4j', 'kuzudb']), 
              help='Graph database type')
@click.option('--db-host', default='localhost', help='Database server host')
@click.option('--db-port', default=None, type=int, 
              help='Database server port (default: memgraph=7687, falkordb=6379, neo4j=7687)')
@click.option('--db-user', default=None, help='Database username')
@click.option('--db-pass', default=None, help='Database password')
@click.option('--db-name', default=None, help='Database name (for Neo4j)')
@click.option('--db-path', default=None, help='Database path (for KuzuDB on-disk mode)')
@click.option('--db-in-memory', is_flag=True, help='Use in-memory mode (for KuzuDB)')
@click.option('--export-dir', type=click.Path(exists=True), required=True, 
              help='Directory to export graph data to')
def export(db_type, db_host, db_port, db_user, db_pass, db_name, db_path, db_in_memory, export_dir):
    """Export the knowledge graph to CSV files."""
    try:
        # Configure storage based on selected database type
        storage_config = {}
        
        # Handle different database types
        if db_type in ["memgraph", "falkordb", "neo4j"]:
            storage_config["host"] = db_host
            
            # Set default ports based on database type if not provided
            if db_port is None:
                if db_type == "memgraph":
                    db_port = 7687
                elif db_type == "falkordb":
                    db_port = 6379
                elif db_type == "neo4j":
                    db_port = 7687
            
            storage_config["port"] = db_port
            
            # Add authentication if provided
            if db_user is not None:
                storage_config["username"] = db_user
            if db_pass is not None:
                storage_config["password"] = db_pass
            
            # Add database name for Neo4j
            if db_type == "neo4j" and db_name is not None:
                storage_config["database"] = db_name
        
        # Handle KuzuDB specific configuration
        elif db_type == "kuzudb":
            if db_path:
                storage_config["db_path"] = db_path
            if db_in_memory:
                storage_config["in_memory"] = True

        # Initialize the graph with the configured storage
        graph = CodeKnowledgeGraph(storage_type=db_type, storage_config=storage_config)
        
        with console.status(f"Exporting graph from {db_type} to {export_dir}...", spinner="dots"):
            graph.export_to_csv(export_dir)
        
        console.print(f"[green]Graph data exported to {export_dir} successfully.[/green]")
    
    except Exception as e:
        console.print(f"[red]Error exporting graph: {e}[/red]")


@cli.command()
@click.option('--db-type', default='memgraph', type=click.Choice(['memgraph', 'falkordb', 'neo4j', 'kuzudb']), 
              help='Graph database type')
@click.option('--db-host', default='localhost', help='Database server host')
@click.option('--db-port', default=None, type=int, 
              help='Database server port (default: memgraph=7687, falkordb=6379, neo4j=7687)')
@click.option('--db-user', default=None, help='Database username')
@click.option('--db-pass', default=None, help='Database password')
@click.option('--db-name', default=None, help='Database name (for Neo4j)')
@click.option('--db-path', default=None, help='Database path (for KuzuDB on-disk mode)')
@click.option('--db-in-memory', is_flag=True, help='Use in-memory mode (for KuzuDB)')
@click.option('--import-dir', type=click.Path(exists=True), required=True, 
              help='Directory to import graph data from')
def import_data(db_type, db_host, db_port, db_user, db_pass, db_name, db_path, db_in_memory, import_dir):
    """Import the knowledge graph from CSV files."""
    try:
        # Configure storage based on selected database type
        storage_config = {}
        
        # Handle different database types
        if db_type in ["memgraph", "falkordb", "neo4j"]:
            storage_config["host"] = db_host
            
            # Set default ports based on database type if not provided
            if db_port is None:
                if db_type == "memgraph":
                    db_port = 7687
                elif db_type == "falkordb":
                    db_port = 6379
                elif db_type == "neo4j":
                    db_port = 7687
            
            storage_config["port"] = db_port
            
            # Add authentication if provided
            if db_user is not None:
                storage_config["username"] = db_user
            if db_pass is not None:
                storage_config["password"] = db_pass
            
            # Add database name for Neo4j
            if db_type == "neo4j" and db_name is not None:
                storage_config["database"] = db_name
        
        # Handle KuzuDB specific configuration
        elif db_type == "kuzudb":
            if db_path:
                storage_config["db_path"] = db_path
            if db_in_memory:
                storage_config["in_memory"] = True

        # Initialize the graph with the configured storage
        graph = CodeKnowledgeGraph(storage_type=db_type, storage_config=storage_config)
        
        with console.status(f"Importing graph to {db_type} from {import_dir}...", spinner="dots"):
            graph.import_from_csv(import_dir)
        
        console.print(f"[green]Graph data imported from {import_dir} successfully.[/green]")
    
    except Exception as e:
        console.print(f"[red]Error importing graph: {e}[/red]")


if __name__ == '__main__':
    cli()