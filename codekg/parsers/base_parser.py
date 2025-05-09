"""
Base parser class for code analysis and knowledge graph construction.
"""
import os
from typing import List, Dict, Set, Optional, Any, Iterator
import logging
import uuid
from abc import ABC, abstractmethod

from tree_sitter import Language, Parser, Tree, Node

from codekg.core import CodeKnowledgeGraph


class BaseParser(ABC):
    """
    Base parser class for extracting code information and building a knowledge graph.
    Each language-specific parser will inherit from this class.
    """
    
    def __init__(self, language_name: str, language_version: str = None):
        """
        Initialize the parser.
        
        Args:
            language_name: Name of the programming language
            language_version: Optional version of the language
        """
        self.language_name = language_name
        self.language_version = language_version
        self.logger = logging.getLogger(f"{__name__}.{language_name}")
        
        # Tree-sitter parser will be initialized in the subclass
        self.parser = None
        self.language = None
        
    @abstractmethod
    def initialize_parser(self) -> None:
        """Initialize the tree-sitter parser with the appropriate language."""
        pass
    
    def parse_file(self, file_path: str, graph: CodeKnowledgeGraph) -> None:
        """
        Parse a single file and add its contents to the knowledge graph.
        
        Args:
            file_path: Path to the file to parse
            graph: Knowledge graph to populate
        """
        if not os.path.exists(file_path):
            self.logger.error(f"File not found: {file_path}")
            return
        
        with open(file_path, 'rb') as f:
            source_code = f.read()
            
        if self.parser is None:
            self.initialize_parser()
            
        try:
            tree = self.parser.parse(source_code)
            self.process_file(file_path, source_code, tree, graph)
        except Exception as e:
            self.logger.error(f"Error parsing {file_path}: {e}")
    
    def parse_directory(self, directory_path: str, graph: CodeKnowledgeGraph,
                        file_extensions: Optional[List[str]] = None) -> None:
        """
        Parse all files in a directory and add them to the knowledge graph.
        
        Args:
            directory_path: Path to the directory to parse
            graph: Knowledge graph to populate
            file_extensions: Optional list of file extensions to include (e.g., ['.java'])
        """
        if not os.path.exists(directory_path):
            self.logger.error(f"Directory not found: {directory_path}")
            return
        
        for root, _, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                
                # Skip files with extensions not in the list
                if file_extensions:
                    ext = os.path.splitext(file_path)[1]
                    if ext.lower() not in file_extensions:
                        continue
                        
                self.parse_file(file_path, graph)
    
    @abstractmethod
    def process_file(self, file_path: str, source_code: bytes, tree: Tree, graph: CodeKnowledgeGraph) -> None:
        """
        Process a parsed file and extract entities and relationships.
        
        Args:
            file_path: Path to the file
            source_code: Raw source code bytes
            tree: Parsed tree-sitter tree
            graph: Knowledge graph to populate
        """
        pass
    
    def walk_tree(self, node: Node, cursor: Optional[Any] = None) -> Iterator[Node]:
        """
        Walk the AST tree in a depth-first order.
        
        Args:
            node: Current tree node
            cursor: Optional cursor for efficient tree traversal
            
        Yields:
            Each node in the tree
        """
        yield node
        
        # Use cursor if provided, otherwise default to child count
        if cursor:
            cursor.reset(node)
            
            if cursor.goto_first_child():
                while True:
                    yield from self.walk_tree(cursor.node, cursor)
                    if not cursor.goto_next_sibling():
                        break
                cursor.goto_parent()
        else:
            for i in range(node.child_count):
                yield from self.walk_tree(node.children[i])
    
    def generate_id(self) -> str:
        """Generate a unique ID for a graph entity."""
        return str(uuid.uuid4())
    
    def extract_node_text(self, node: Node, source_code: bytes) -> str:
        """
        Extract the text for a given node from the source code.
        
        Args:
            node: Tree-sitter node
            source_code: Original source code bytes
            
        Returns:
            Text content of the node
        """
        return source_code[node.start_byte:node.end_byte].decode('utf-8', errors='replace') 