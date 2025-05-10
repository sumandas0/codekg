"""
Java-specific parser for extracting code information.
"""
import os
from typing import Dict, List, Optional, Set, Any, Tuple
import logging
from pathlib import Path
import sys
import re
import uuid

import tree_sitter_java
from tree_sitter import Language, Parser, Tree, Node, Query

from codekg.core import (
    CodeKnowledgeGraph,
    File,
    Namespace,
    Structure,
    Callable,
    Parameter,
    Variable,
    Annotation,
    Comment,
    DefinedIn,
    Contains,
    Calls,
    HasParameter,
    References,
    Accesses,
    InheritsFrom,
    Implements,
    Imports
)
from .base_parser import BaseParser


# Debug test function to help figure out the correct tree-sitter usage
def _test_parser_init():
    """Test different ways to initialize the parser."""
    try:
        # Try to get a parser working
        parser = Parser()
        lang = tree_sitter_java.language()
        print(f"Parser: {parser}")
        print(f"Language type: {type(lang)}")
        print(f"Parser language before: {parser.language}")
        try:
            print("Setting language with attribute assignment...")
            parser.language = lang
            print(f"Parser language after: {parser.language}")
        except Exception as e1:
            print(f"Attribute assignment failed: {e1}")
            try:
                # Maybe there's a different way?
                print("Checking alternative methods...")
                print(f"Parser dir: {dir(parser)}")
            except Exception as e2:
                print(f"Alternative lookup failed: {e2}")
    except Exception as e:
        print(f"Test function failed: {e}")

    return None


class JavaParser(BaseParser):
    """
    Parser for Java source code.
    """
    
    @staticmethod
    def diagnose_tree_sitter_installation():
        """
        Diagnose tree-sitter and tree-sitter-java installation.
        Returns a diagnostic report as a string.
        """
        report = []
        report.append("=== Tree-Sitter Diagnostic Report ===")
        
        # Check tree-sitter package
        try:
            import tree_sitter
            report.append(f"✓ tree-sitter package found (version: {getattr(tree_sitter, '__version__', 'unknown')})")
            report.append(f"  - Location: {tree_sitter.__file__}")
        except ImportError:
            report.append("✗ tree-sitter package not found!")
        
        # Check tree-sitter-java package
        try:
            import tree_sitter_java
            report.append(f"✓ tree-sitter-java package found")
            report.append(f"  - Location: {tree_sitter_java.__file__}")
            
            # Check if language function exists
            if hasattr(tree_sitter_java, 'language'):
                report.append("✓ tree-sitter-java.language() function found")
                try:
                    lang = tree_sitter_java.language()
                    report.append("✓ tree-sitter-java.language() executed successfully")
                except Exception as e:
                    report.append(f"✗ tree-sitter-java.language() execution failed: {e}")
            else:
                report.append("✗ tree-sitter-java.language() function not found!")
            
        except ImportError:
            report.append("✗ tree-sitter-java package not found!")
        
        # Check Parser
        try:
            parser = tree_sitter.Parser()
            report.append("✓ Successfully created Parser instance")
            
            # Try to set language
            try:
                parser.set_language(tree_sitter_java.language())
                report.append("✓ Successfully set Java language in parser")
            except Exception as e:
                report.append(f"✗ Failed to set language in parser: {e}")
        except Exception as e:
            report.append(f"✗ Failed to create Parser instance: {e}")
        
        return "\n".join(report)

    def __init__(self):
        """Initialize the Java parser."""
        super().__init__("java", "1.8+")
        self.language = None
        self.parser = None
        
        # Track current scope for qualified name generation
        self.current_package = ""
        self.current_class_stack = []
        
        # Map nodes to their IDs for easy lookup later
        self.node_to_id_map = {}
        
        # Run diagnostic at init time
        diagnostic_report = self.diagnose_tree_sitter_installation()
        self.logger.info(f"Java parser initialization diagnostic:\n{diagnostic_report}")
        
    def generate_id(self) -> str:
        """Generate a unique ID for entities."""
        return str(uuid.uuid4())
        
    def initialize_parser(self) -> None:
        """Initialize the tree-sitter parser with the Java grammar."""
        try:
            self.logger.info("Initializing Java parser with tree-sitter...")
            try:
                import tree_sitter
                # Check if tree_sitter_java module is properly loaded
                import importlib
                tree_sitter_java_spec = importlib.util.find_spec("tree_sitter_java")
                if tree_sitter_java_spec is None:
                    self.logger.error("tree_sitter_java module not found")
                    raise ImportError("tree_sitter_java module not found")
                self.logger.info(f"tree_sitter_java found at: {tree_sitter_java_spec.origin}")
                
                # Try to get language object
                self.parser = Parser()
                self.logger.info("Parser instance created")
                
                # Get Java language
                language_capsule = tree_sitter_java.language()
                self.logger.info(f"Java language loaded (type: {type(language_capsule).__name__})")
                
                # Convert PyCapsule to Language if needed
                if hasattr(tree_sitter, 'Language') and not isinstance(language_capsule, tree_sitter.Language):
                    self.logger.info("Converting PyCapsule to Language object")
                    try:
                        self.language = tree_sitter.Language(language_capsule)
                    except Exception as e:
                        self.logger.error(f"Failed to convert language: {e}")
                        # Try direct assignment as fallback
                        self.language = language_capsule
                else:
                    self.language = language_capsule
                
                # Check if parser has set_language method or language attribute
                if hasattr(self.parser, 'set_language'):
                    self.logger.info("Using parser.set_language() method")
                    self.parser.set_language(self.language)
                elif hasattr(self.parser, 'language'):
                    self.logger.info("Using parser.language attribute")
                    self.parser.language = self.language
                else:
                    self.logger.error("Parser has no method to set language!")
                    raise AttributeError("Parser has neither set_language method nor language attribute")
                
                self.logger.info("Language set in parser successfully")
                
                # Test if parser works with a simple Java code
                test_code = b"public class Test { }"
                test_tree = self.parser.parse(test_code)
                self.logger.info(f"Parser test successful, root node type: {test_tree.root_node.type}")
                
            except AttributeError as ae:
                self.logger.error(f"AttributeError when initializing tree-sitter: {ae}")
                self.logger.error("This likely means tree_sitter_java module doesn't have the expected functions or attributes")
                raise
            except ImportError as ie:
                self.logger.error(f"ImportError when initializing tree-sitter: {ie}")
                self.logger.error("Check if tree_sitter_java is installed correctly")
                raise
        except Exception as e:
            self.logger.error(f"Failed to initialize Java parser: {e}")
            self.logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            raise
            
    def parse_file(self, file_path: str, graph: CodeKnowledgeGraph) -> None:
        """
        Parse a Java file and extract its contents into the knowledge graph.
        
        Args:
            file_path: Path to the Java file
            graph: Knowledge graph to populate
        """
        try:
            # Read file contents
            with open(file_path, 'rb') as f:
                source_code = f.read()
                
            # Initialize parser if needed
            if self.parser is None:
                self.initialize_parser()
            
            try:
                # Attempt to parse the file with tree-sitter
                self.logger.info(f"Parsing {file_path} with tree-sitter...")
                tree = self.parser.parse(source_code)
                self.logger.info(f"Tree-sitter parse successful for {file_path}")
                
                # Process the file with the parsed tree
                self.process_file(file_path, source_code, tree, graph)
                self.logger.info(f"Processed {file_path}")
            except Exception as parse_error:
                # Log detailed error info but DO NOT fall back to regex
                self.logger.error(f"Tree-sitter parsing failed for {file_path}: {parse_error}")
                self.logger.error(f"Error type: {type(parse_error).__name__}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                
                if isinstance(parse_error, (AttributeError, TypeError)):
                    self.logger.error("This might indicate a problem with tree-sitter configuration or language binding")
                elif isinstance(parse_error, MemoryError):
                    self.logger.error("Memory error encountered - file might be too large")
                
                # Raise exception instead of falling back to regex
                raise RuntimeError(f"Tree-sitter parsing failed and regex fallback is disabled for {file_path}") from parse_error
                
        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {e}")
            # Continue with other files instead of raising
            return
            
    def process_file(self, file_path: str, source_code: bytes, tree, graph: CodeKnowledgeGraph) -> None:
        """
        Process a Java file and extract its contents into the knowledge graph.
        
        Args:
            file_path: Path to the Java file
            source_code: Raw source code bytes
            tree: Parsed tree-sitter tree
            graph: Knowledge graph to populate
        """
        # Reset current scope
        self.current_package = ""
        self.current_class_stack = []
        self.node_to_id_map = {}
        
        # Create File entity
        file_id = self.generate_id()
        file_name = os.path.basename(file_path)
        file_path_str = str(Path(file_path).resolve())
        file_entity = File(
            id=file_id,
            name=file_name,
            qualified_name=file_path_str,
            path=file_path_str,
            language="java"
        )
        graph.add_entity(file_entity)
        
        # Extract package declaration
        self._extract_package(tree.root_node, source_code, graph, file_id)
        
        # Extract imports
        self._extract_imports(tree.root_node, source_code, graph, file_id)
        
        # Extract classes and interfaces
        self._extract_classes_and_interfaces(tree.root_node, source_code, graph, file_id)
            
    def _extract_package(self, root_node: Node, source_code: bytes, graph: CodeKnowledgeGraph, file_id: str) -> None:
        """Extract package declaration from file."""
        package_declaration = self._find_first_node(root_node, "package_declaration")
        if package_declaration:
            name_node = self._find_first_node(package_declaration, "scoped_identifier")
            if name_node:
                package_name = self._get_node_text(name_node, source_code)
                self.current_package = package_name
                
                # Create package entity
                package_id = self.generate_id()
                package_entity = Namespace(
                    id=package_id,
                    name=package_name,
                    qualified_name=package_name,
                    language="java"
                )
                graph.add_entity(package_entity)
                
                # Add DEFINED_IN relationship
                defined_in = DefinedIn(
                    source=package_id,
                    target=file_id,
                    line_number_start=package_declaration.start_point[0] + 1,
                    line_number_end=package_declaration.end_point[0] + 1
                )
                graph.add_relationship(defined_in)
        else:
            # Default package
            self.current_package = "default"
            package_id = self.generate_id()
            package_entity = Namespace(
                id=package_id,
                name="default",
                qualified_name="default",
                language="java"
            )
            graph.add_entity(package_entity)
            defined_in = DefinedIn(
                source=package_id,
                target=file_id,
                line_number_start=1,
                line_number_end=1
            )
            graph.add_relationship(defined_in)
    
    def _extract_imports(self, root_node: Node, source_code: bytes, graph: CodeKnowledgeGraph, file_id: str) -> None:
        """Extract import statements from file."""
        import_declarations = self._find_nodes(root_node, "import_declaration")
        for import_decl in import_declarations:
            name_node = self._find_first_node(import_decl, "scoped_identifier")
            if name_node:
                import_name = self._get_node_text(name_node, source_code)
                
                # Create import entity (as a namespace)
                import_id = self.generate_id()
                import_entity = Namespace(
                    id=import_id,
                    name=import_name.split('.')[-1],
                    qualified_name=import_name,
                    language="java"
                )
                graph.add_entity(import_entity)
                
                # Add IMPORTS relationship between file and import
                imports = Imports(
                    source=file_id,
                    target=import_id,
                    line_number_start=import_decl.start_point[0] + 1,
                    line_number_end=import_decl.end_point[0] + 1
                )
                graph.add_relationship(imports)
                
    def _extract_classes_and_interfaces(self, root_node: Node, source_code: bytes, graph: CodeKnowledgeGraph, file_id: str) -> None:
        """Extract classes and interfaces from file."""
        # Find all class and interface declarations
        class_declarations = self._find_nodes(root_node, "class_declaration")
        interface_declarations = self._find_nodes(root_node, "interface_declaration")
        enum_declarations = self._find_nodes(root_node, "enum_declaration")
        
        # Process all type declarations
        for decl in class_declarations + interface_declarations + enum_declarations:
            self._process_type_declaration(decl, source_code, graph, file_id)
            
    def _process_type_declaration(self, node: Node, source_code: bytes, graph: CodeKnowledgeGraph, file_id: str) -> None:
        """Process a class, interface, or enum declaration."""
        # Get type of declaration
        node_type = node.type
        is_interface = node_type == "interface_declaration"
        is_enum = node_type == "enum_declaration"
        
        # Get name
        identifier_node = self._find_first_node(node, "identifier")
        if not identifier_node:
            return
        
        name = self._get_node_text(identifier_node, source_code)
        
        # Determine qualified name
        qualified_name = name
        if self.current_package and self.current_package != "default":
            qualified_name = f"{self.current_package}.{name}"
        
        # Get modifiers
        modifiers = []
        modifiers_node = node.parent
        if modifiers_node and modifiers_node.type == "modifiers":
            for i in range(modifiers_node.child_count):
                modifier = modifiers_node.children[i]
                modifiers.append(modifier.type)
        
        # Determine access modifier
        access_modifier = "default"
        if "public" in modifiers:
            access_modifier = "public"
        elif "protected" in modifiers:
            access_modifier = "protected"
        elif "private" in modifiers:
            access_modifier = "private"
        
        # Determine if abstract
        is_abstract = "abstract" in modifiers or is_interface
        
        # Create Structure entity
        structure_id = self.generate_id()
        structure = Structure(
            id=structure_id,
            name=name,
            qualified_name=qualified_name,
            language="java",
            access_modifier=access_modifier,
            is_abstract=is_abstract,
            is_interface=is_interface
        )
        graph.add_entity(structure)
        
        # Add DEFINED_IN relationship
        defined_in = DefinedIn(
            source=structure_id,
            target=file_id,
            line_number_start=node.start_point[0] + 1,
            line_number_end=node.end_point[0] + 1
        )
        graph.add_relationship(defined_in)
        
        # Add CONTAINS relationship between package and class
        if self.current_package:
            # Find the package entity
            package_entities = [e for e_id, e in graph.entities.items() 
                              if isinstance(e, Namespace) and e.name == self.current_package]
            if package_entities:
                package_entity = package_entities[0]
                contains = Contains(
                    source=package_entity.id,
                    target=structure_id
                )
                graph.add_relationship(contains)
        
        # Check for superclass (extends)
        if node_type == "class_declaration":
            superclass_node = self._find_first_node(node, "superclass")
            if superclass_node:
                type_node = self._find_first_node(superclass_node, "type_identifier") or self._find_first_node(superclass_node, "scoped_type_identifier")
                if type_node:
                    superclass_name = self._get_node_text(type_node, source_code)
                    
                    # Create superclass entity
                    superclass_id = self.generate_id()
                    superclass = Structure(
                        id=superclass_id,
                        name=superclass_name.split('.')[-1],
                        qualified_name=superclass_name,
                        language="java"
                    )
                    graph.add_entity(superclass)
                    
                    # Add INHERITS_FROM relationship
                    inherits = InheritsFrom(
                        source=structure_id,
                        target=superclass_id
                    )
                    graph.add_relationship(inherits)
                    
        # Check for implemented interfaces
        interfaces_node = self._find_first_node(node, "interfaces")
        if interfaces_node:
            interface_types = self._find_nodes(interfaces_node, "type_identifier") + self._find_nodes(interfaces_node, "scoped_type_identifier")
            for interface_type in interface_types:
                interface_name = self._get_node_text(interface_type, source_code)
                
                # Create interface entity
                interface_id = self.generate_id()
                interface = Structure(
                    id=interface_id,
                    name=interface_name.split('.')[-1],
                    qualified_name=interface_name,
                    language="java",
                    is_interface=True
                )
                graph.add_entity(interface)
                
                # Add IMPLEMENTS relationship
                implements = Implements(
                    source=structure_id,
                    target=interface_id
                )
                graph.add_relationship(implements)
        
        # Save current class for inner class processing
        self.current_class_stack.append((name, qualified_name))
        
        # Extract fields
        body_node = self._find_first_node(node, "class_body") or self._find_first_node(node, "interface_body") or self._find_first_node(node, "enum_body")
        if body_node:
            # Process fields
            field_declarations = self._find_nodes(body_node, "field_declaration")
            for field_decl in field_declarations:
                self._process_field_declaration(field_decl, source_code, graph, structure_id)
            
            # Process methods
            method_declarations = self._find_nodes(body_node, "method_declaration")
            constructor_declarations = self._find_nodes(body_node, "constructor_declaration")
            
            for method_decl in method_declarations + constructor_declarations:
                self._process_method_declaration(method_decl, source_code, graph, structure_id)
        
        # Extract inner classes recursively
        inner_classes = self._find_nodes(body_node, "class_declaration") if body_node else []
        inner_interfaces = self._find_nodes(body_node, "interface_declaration") if body_node else []
        inner_enums = self._find_nodes(body_node, "enum_declaration") if body_node else []
        
        for inner_type in inner_classes + inner_interfaces + inner_enums:
            self._process_type_declaration(inner_type, source_code, graph, file_id)
            
        # Remove current class from stack
        self.current_class_stack.pop()
    
    def _process_field_declaration(self, node: Node, source_code: bytes, graph: CodeKnowledgeGraph, class_id: str) -> None:
        """Process a field declaration."""
        # Get type
        type_node = self._find_first_node(node, "type_identifier") or self._find_first_node(node, "scoped_type_identifier")
        if not type_node:
            return
            
        field_type = self._get_node_text(type_node, source_code)
        
        # Process variable declarators
        variable_declarators = self._find_nodes(node, "variable_declarator")
        for var_decl in variable_declarators:
            name_node = self._find_first_node(var_decl, "identifier")
            if not name_node:
                continue
                
            field_name = self._get_node_text(name_node, source_code)
            
            # Determine qualified name
            if self.current_class_stack:
                qualified_name = f"{self.current_class_stack[-1][1]}.{field_name}"
            else:
                qualified_name = field_name
                
            # Get modifiers
            modifiers = []
            modifiers_node = node.parent
            if modifiers_node and modifiers_node.type == "modifiers":
                for i in range(modifiers_node.child_count):
                    modifier = modifiers_node.children[i]
                    modifiers.append(modifier.type)
            
            # Determine access modifier
            access_modifier = "default"
            if "public" in modifiers:
                access_modifier = "public"
            elif "protected" in modifiers:
                access_modifier = "protected"
            elif "private" in modifiers:
                access_modifier = "private"
                
            # Check if constant
            is_constant = "final" in modifiers
            
            # Get initial value if any
            initial_value = None
            value_node = self._find_first_node(var_decl, "initializer")
            if value_node:
                initial_value = self._get_node_text(value_node, source_code)
            
            # Create Variable entity
            variable_id = self.generate_id()
            variable = Variable(
                id=variable_id,
                name=field_name,
                qualified_name=qualified_name,
                language="java",
                type=field_type,
                initial_value=initial_value,
                is_constant=is_constant,
                access_modifier=access_modifier
            )
            graph.add_entity(variable)
            
            # Add CONTAINS relationship between class and field
            contains = Contains(
                source=class_id,
                target=variable_id,
                line_number_start=node.start_point[0] + 1,
                line_number_end=node.end_point[0] + 1
            )
            graph.add_relationship(contains)
    
    def _process_method_declaration(self, node: Node, source_code: bytes, graph: CodeKnowledgeGraph, class_id: str) -> None:
        """Process a method or constructor declaration."""
        is_constructor = node.type == "constructor_declaration"
        
        # Get name
        name_node = self._find_first_node(node, "identifier")
        if not name_node:
            return
            
        method_name = self._get_node_text(name_node, source_code)
        
        # Determine qualified name
        if self.current_class_stack:
            qualified_name = f"{self.current_class_stack[-1][1]}.{method_name}"
        else:
            qualified_name = method_name
            
        # Get return type for methods
        return_type = None
        if not is_constructor:
            return_type_node = self._find_first_node(node, "type_identifier") or self._find_first_node(node, "scoped_type_identifier") or self._find_first_node(node, "primitive_type") or self._find_first_node(node, "void_type")
            if return_type_node:
                return_type = self._get_node_text(return_type_node, source_code)
        
        # Get modifiers
        modifiers = []
        modifiers_node = node.parent
        if modifiers_node and modifiers_node.type == "modifiers":
            for i in range(modifiers_node.child_count):
                modifier = modifiers_node.children[i]
                modifiers.append(modifier.type)
        
        # Determine access modifier
        access_modifier = "default"
        if "public" in modifiers:
            access_modifier = "public"
        elif "protected" in modifiers:
            access_modifier = "protected"
        elif "private" in modifiers:
            access_modifier = "private"
            
        # Check if static or abstract
        is_static = "static" in modifiers
        is_abstract = "abstract" in modifiers
        
        # Get method signature
        signature = method_name
        if node.child_by_field_name('parameters'):
            param_list = []
            formal_params = self._find_first_node(node, "formal_parameters")
            if formal_params:
                params = self._find_nodes(formal_params, "formal_parameter")
                for param in params:
                    param_type_node = self._find_first_node(param, "type_identifier") or self._find_first_node(param, "scoped_type_identifier") or self._find_first_node(param, "primitive_type")
                    if param_type_node:
                        param_list.append(self._get_node_text(param_type_node, source_code))
            signature = f"{method_name}({', '.join(param_list)})"
        
        # Create Callable entity
        callable_id = self.generate_id()
        callable_entity = Callable(
            id=callable_id,
            name=method_name,
            qualified_name=qualified_name,
            language="java",
            return_type=return_type,
            access_modifier=access_modifier,
            is_static=is_static,
            is_abstract=is_abstract,
            signature=signature
        )
        graph.add_entity(callable_entity)
        
        # Add DEFINED_IN relationship
        contains = Contains(
            source=class_id,
            target=callable_id,
            line_number_start=node.start_point[0] + 1,
            line_number_end=node.end_point[0] + 1
        )
        graph.add_relationship(contains)
        
        # Process parameters
        formal_params = self._find_first_node(node, "formal_parameters")
        if formal_params:
            params = self._find_nodes(formal_params, "formal_parameter")
            for i, param in enumerate(params):
                param_type_node = self._find_first_node(param, "type_identifier") or self._find_first_node(param, "scoped_type_identifier") or self._find_first_node(param, "primitive_type")
                param_name_node = self._find_first_node(param, "identifier")
                
                if param_type_node and param_name_node:
                    param_type = self._get_node_text(param_type_node, source_code)
                    param_name = self._get_node_text(param_name_node, source_code)
                    
                    # Create Parameter entity
                    param_id = self.generate_id()
                    param_entity = Parameter(
                        id=param_id,
                        name=param_name,
                        qualified_name=f"{qualified_name}.{param_name}",
                        language="java",
                        type=param_type,
                        position=i
                    )
                    graph.add_entity(param_entity)
                    
                    # Add HAS_PARAMETER relationship
                    has_param = HasParameter(
                        source=callable_id,
                        target=param_id,
                        line_number_start=param.start_point[0] + 1,
                        line_number_end=param.end_point[0] + 1
                    )
                    graph.add_relationship(has_param)
        
        # Process method body to extract method calls
        body = self._find_first_node(node, "block")
        if body:
            self._process_method_body(body, source_code, graph, callable_id)
            
    def _process_method_body(self, body: Node, source_code: bytes, graph: CodeKnowledgeGraph, method_id: str) -> None:
        """Process method body to extract calls and references."""
        # Extract method calls
        method_invocations = self._find_nodes_recursively(body, "method_invocation")
        for invocation in method_invocations:
            name_node = self._find_first_node(invocation, "identifier")
            if name_node:
                method_name = self._get_node_text(name_node, source_code)
                
                # Create a placeholder Callable for the called method
                called_id = self.generate_id()
                called_entity = Callable(
                    id=called_id,
                    name=method_name,
                    qualified_name=method_name,  # Simplified qualified name
                    language="java"
                )
                graph.add_entity(called_entity)
                
                # Add CALLS relationship
                calls = Calls(
                    source=method_id,
                    target=called_id,
                    line_number_start=invocation.start_point[0] + 1,
                    line_number_end=invocation.end_point[0] + 1
                )
                graph.add_relationship(calls)
                
    def _find_first_node(self, node: Node, node_type: str) -> Optional[Node]:
        """Find the first node of the given type in the subtree."""
        if node.type == node_type:
            return node
            
        for i in range(node.child_count):
            child = node.children[i]
            result = self._find_first_node(child, node_type)
            if result:
                return result
                
        return None
        
    def _find_nodes(self, node: Node, node_type: str) -> List[Node]:
        """Find all nodes of the given type in the immediate children."""
        results = []
        for i in range(node.child_count):
            child = node.children[i]
            if child.type == node_type:
                results.append(child)
            # For compound statements like field_declaration, class_body, etc.
            results.extend(self._find_nodes(child, node_type))
        return results
        
    def _find_nodes_recursively(self, node: Node, node_type: str) -> List[Node]:
        """Find all nodes of the given type in the subtree."""
        results = []
        if node.type == node_type:
            results.append(node)
            
        for i in range(node.child_count):
            child = node.children[i]
            results.extend(self._find_nodes_recursively(child, node_type))
            
        return results
        
    def _get_node_text(self, node: Node, source_code: bytes) -> str:
        """Get text for a node from the source code."""
        start_byte = node.start_byte
        end_byte = node.end_byte
        return source_code[start_byte:end_byte].decode('utf-8')

    def process_file_with_regex(self, file_path: str, source_code: bytes, graph: CodeKnowledgeGraph) -> None:
        """
        Process a Java file using regex extraction when tree-sitter parsing fails.
        
        Args:
            file_path: Path to the Java file
            source_code: Raw source code bytes
            graph: Knowledge graph to populate
        """
        import re
        # Create File entity
        file_id = self.generate_id()
        file_name = os.path.basename(file_path)
        file_path_str = str(Path(file_path).resolve())
        file_entity = File(
            id=file_id,
            name=file_name,
            qualified_name=file_path_str,
            path=file_path_str,
            language="java"
        )
        graph.add_entity(file_entity)
        
        source_str = source_code.decode('utf-8', errors='replace')
        lines = source_str.split('\n')
        
        # Extract package
        package_match = re.search(r'package\s+([a-zA-Z0-9_.]+);', source_str)
        package_name = "default"
        if package_match:
            package_name = package_match.group(1)
            self.current_package = package_name
            
            # Create package entity
            package_id = self.generate_id()
            package_entity = Namespace(
                id=package_id,
                name=package_name,
                qualified_name=package_name,
                language="java"
            )
            graph.add_entity(package_entity)
            
            # Add DEFINED_IN relationship
            defined_in = DefinedIn(
                source=package_id,
                target=file_id,
                line_number_start=1,  # Approximation
                line_number_end=1
            )
            graph.add_relationship(defined_in)
        
        # Extract imports
        import_matches = re.finditer(r'import\s+([a-zA-Z0-9_.]+);', source_str)
        for import_match in import_matches:
            import_name = import_match.group(1)
            
            # Create import entity
            import_id = self.generate_id()
            import_entity = Namespace(
                id=import_id,
                name=import_name.split('.')[-1],
                qualified_name=import_name,
                language="java"
            )
            graph.add_entity(import_entity)
            
            # Add IMPORTS relationship
            imports = Imports(
                source=file_id,
                target=import_id
            )
            graph.add_relationship(imports)
        
        # Extract classes/interfaces
        class_pattern = r'(?:public|protected|private|)\s+(?:abstract|final|)?\s*(?:class|interface|enum)\s+([A-Za-z0-9_]+)(?:\s+extends\s+([A-Za-z0-9_.<>]+))?(?:\s+implements\s+([A-Za-z0-9_.<>, ]+))?'
        class_matches = re.finditer(class_pattern, source_str)
        
        for class_match in class_matches:
            class_name = class_match.group(1)
            extends_name = class_match.group(2) if class_match.lastindex >= 2 else None
            implements_str = class_match.group(3) if class_match.lastindex >= 3 else None
            
            # Determine qualified name
            qualified_name = class_name
            if package_name and package_name != "default":
                qualified_name = f"{package_name}.{class_name}"
            
            # Determine if it's an interface or enum
            class_definition = class_match.group(0)
            is_interface = "interface" in class_definition
            is_enum = "enum" in class_definition
            
            # Create Structure entity
            class_id = self.generate_id()
            class_entity = Structure(
                id=class_id,
                name=class_name,
                qualified_name=qualified_name,
                language="java",
                access_modifier="public" if "public" in class_definition else "default",
                is_abstract="abstract" in class_definition or is_interface,
                is_interface=is_interface
            )
            graph.add_entity(class_entity)
            
            # Add DEFINED_IN relationship
            defined_in = DefinedIn(
                source=class_id,
                target=file_id
            )
            graph.add_relationship(defined_in)
            
            # Add CONTAINS relationship between package and class
            if package_name:
                # Find the package entity
                package_entities = [e for e_id, e in graph.entities.items() 
                                  if isinstance(e, Namespace) and e.name == package_name]
                if package_entities:
                    package_entity = package_entities[0]
                    contains = Contains(
                        source=package_entity.id,
                        target=class_id
                    )
                    graph.add_relationship(contains)
            
            # Handle inheritance
            if extends_name:
                superclass_id = self.generate_id()
                superclass = Structure(
                    id=superclass_id,
                    name=extends_name.split('.')[-1],
                    qualified_name=extends_name,
                    language="java"
                )
                graph.add_entity(superclass)
                
                inherits = InheritsFrom(
                    source=class_id,
                    target=superclass_id
                )
                graph.add_relationship(inherits)
            
            # Handle interfaces
            if implements_str:
                interfaces = [i.strip() for i in implements_str.split(',')]
                for interface_name in interfaces:
                    interface_id = self.generate_id()
                    interface = Structure(
                        id=interface_id,
                        name=interface_name.split('.')[-1],
                        qualified_name=interface_name,
                        language="java",
                        is_interface=True
                    )
                    graph.add_entity(interface)
                    
                    implements = Implements(
                        source=class_id,
                        target=interface_id
                    )
                    graph.add_relationship(implements)
            
            # Extract methods with regex
            # First, find the class body
            class_start = class_match.end()
            open_braces = 1
            class_end = class_start
            in_class_body = False
            
            # Simple but imperfect approach to find the class body
            for i, char in enumerate(source_str[class_start:], class_start):
                if char == '{':
                    if not in_class_body:
                        in_class_body = True
                    else:
                        open_braces += 1
                elif char == '}':
                    open_braces -= 1
                    if open_braces == 0:
                        class_end = i
                        break
            
            if class_end > class_start:
                class_body = source_str[class_start:class_end]
                
                # Extract methods
                method_pattern = r'(?:public|protected|private|)\s+(?:static|final|abstract|synchronized|native|)?\s*(?:[A-Za-z0-9_.<>\[\]]+)\s+([A-Za-z0-9_]+)\s*\(([^)]*)\)'
                method_matches = re.finditer(method_pattern, class_body)
                
                for method_match in method_matches:
                    method_name = method_match.group(1)
                    params_str = method_match.group(2)
                    
                    # Skip constructors (methods with same name as class)
                    if method_name == class_name:
                        continue
                    
                    # Create Callable entity
                    method_id = self.generate_id()
                    method_entity = Callable(
                        id=method_id,
                        name=method_name,
                        qualified_name=f"{qualified_name}.{method_name}",
                        language="java",
                        signature=f"{method_name}({params_str})"
                    )
                    graph.add_entity(method_entity)
                    
                    # Add CONTAINS relationship
                    contains = Contains(
                        source=class_id,
                        target=method_id
                    )
                    graph.add_relationship(contains)
                    
                # Extract constructors
                constructor_pattern = f'(?:public|protected|private|)\s+{class_name}\s*\(([^)]*)\)'
                constructor_matches = re.finditer(constructor_pattern, class_body)
                
                for constructor_match in constructor_matches:
                    params_str = constructor_match.group(1)
                    
                    # Create Callable entity for constructor
                    constructor_id = self.generate_id()
                    constructor_entity = Callable(
                        id=constructor_id,
                        name=class_name,
                        qualified_name=f"{qualified_name}.{class_name}",
                        language="java",
                        signature=f"{class_name}({params_str})"
                    )
                    graph.add_entity(constructor_entity)
                    
                    # Add CONTAINS relationship
                    contains = Contains(
                        source=class_id,
                        target=constructor_id
                    )
                    graph.add_relationship(contains)
                    
                # Extract fields
                field_pattern = r'(?:public|protected|private|)\s+(?:static|final|)?\s*(?:[A-Za-z0-9_.<>\[\]]+)\s+([A-Za-z0-9_]+)\s*(?:=\s*[^;]+)?;'
                field_matches = re.finditer(field_pattern, class_body)
                
                for field_match in field_matches:
                    field_name = field_match.group(1)
                    field_declaration = field_match.group(0)
                    
                    # Create Variable entity
                    field_id = self.generate_id()
                    field_entity = Variable(
                        id=field_id,
                        name=field_name,
                        qualified_name=f"{qualified_name}.{field_name}",
                        language="java",
                        type="unknown",  # We would need more complex parsing to get the type accurately
                        is_constant="final" in field_declaration,
                        access_modifier="public" if "public" in field_declaration else 
                                      "protected" if "protected" in field_declaration else
                                      "private" if "private" in field_declaration else "default"
                    )
                    graph.add_entity(field_entity)
                    
                    # Add CONTAINS relationship
                    contains = Contains(
                        source=class_id,
                        target=field_id
                    )
                    graph.add_relationship(contains)
            
        self.logger.info(f"Processed {file_path} with regex fallback") 