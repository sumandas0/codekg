"""
Tests for the parsers module.
"""
import unittest
import tempfile
import os
from pathlib import Path

from codekg.core import CodeKnowledgeGraph
from codekg.parsers import JavaParser, PythonParser


class TestParsers(unittest.TestCase):
    """Test cases for language parsers."""
    
    def test_python_parser_init(self):
        """Test that the Python parser can be initialized."""
        parser = PythonParser()
        parser.initialize_parser()
        self.assertIsNotNone(parser.language)
        self.assertIsNotNone(parser.parser)
    
    def test_java_parser_init(self):
        """Test that the Java parser can be initialized."""
        parser = JavaParser()
        parser.initialize_parser()
        self.assertIsNotNone(parser.language)
        self.assertIsNotNone(parser.parser)
    
    def test_python_parse_simple_file(self):
        """Test parsing a simple Python file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple Python file
            python_code = """
# Sample Python file
class MyClass:
    \"\"\"A simple class.\"\"\"
    
    def __init__(self, value):
        self.value = value
    
    def get_value(self):
        \"\"\"Return the value.\"\"\"
        return self.value

def main():
    obj = MyClass(42)
    print(obj.get_value())

if __name__ == "__main__":
    main()
"""
            file_path = os.path.join(tmpdir, "sample.py")
            with open(file_path, "w") as f:
                f.write(python_code)
            
            # Parse the file
            graph = CodeKnowledgeGraph()
            parser = PythonParser()
            parser.parse_file(file_path, graph)
            
            # Verify entities were created
            self.assertGreater(len(graph.entities), 0)
            
            # Verify we have a class
            structures = [e for e in graph.entities.values() if e.__class__.__name__ == "Structure"]
            self.assertEqual(len(structures), 1)
            self.assertEqual(structures[0].name, "MyClass")
            
            # Verify we have methods
            callables = [e for e in graph.entities.values() if e.__class__.__name__ == "Callable"]
            self.assertGreaterEqual(len(callables), 3)  # __init__, get_value, main
    
    def test_java_parse_simple_file(self):
        """Test parsing a simple Java file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple Java file
            java_code = """
package com.example;

/**
 * A simple class.
 */
public class MyClass {
    private int value;
    
    public MyClass(int value) {
        this.value = value;
    }
    
    /**
     * Return the value.
     */
    public int getValue() {
        return value;
    }
    
    public static void main(String[] args) {
        MyClass obj = new MyClass(42);
        System.out.println(obj.getValue());
    }
}
"""
            file_path = os.path.join(tmpdir, "MyClass.java")
            with open(file_path, "w") as f:
                f.write(java_code)
            
            # Parse the file
            graph = CodeKnowledgeGraph()
            parser = JavaParser()
            parser.parse_file(file_path, graph)
            
            # Verify entities were created
            self.assertGreater(len(graph.entities), 0)
            
            # Verify we have a package
            namespaces = [e for e in graph.entities.values() if e.__class__.__name__ == "Namespace"]
            self.assertGreaterEqual(len(namespaces), 1)
            
            # Verify we have a class
            structures = [e for e in graph.entities.values() if e.__class__.__name__ == "Structure"]
            self.assertEqual(len(structures), 1)
            self.assertEqual(structures[0].name, "MyClass")


if __name__ == "__main__":
    unittest.main() 