#!/usr/bin/env python
"""
Diagnostic script to check tree-sitter installation.
"""

import sys
import importlib.util
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_tree_sitter():
    """Check if tree-sitter is properly installed and configured."""
    logger.info("=== Tree-Sitter Diagnostic Report ===")
    
    # Python version
    logger.info(f"Python version: {sys.version}")
    
    # Check tree-sitter package
    try:
        import tree_sitter
        logger.info(f"✓ tree-sitter package found (version: {getattr(tree_sitter, '__version__', 'unknown')})")
        logger.info(f"  - Location: {tree_sitter.__file__}")
        
        # Check Parser class
        logger.info("Testing Parser creation...")
        parser = tree_sitter.Parser()
        logger.info("✓ Successfully created Parser instance")
    except ImportError:
        logger.error("✗ tree-sitter package not found!")
        return False
    except Exception as e:
        logger.error(f"✗ Error when using tree-sitter: {e}")
        return False
    
    # Check tree-sitter-java package
    try:
        import tree_sitter_java
        logger.info(f"✓ tree-sitter-java package found")
        logger.info(f"  - Location: {tree_sitter_java.__file__}")
        
        # Check if language function exists
        if hasattr(tree_sitter_java, 'language'):
            logger.info("✓ tree-sitter-java.language() function found")
            
            # Test language function
            try:
                language_capsule = tree_sitter_java.language()
                logger.info(f"✓ tree-sitter-java.language() executed successfully (type: {type(language_capsule).__name__})")
                
                # Convert PyCapsule to Language if needed
                if hasattr(tree_sitter, 'Language') and not isinstance(language_capsule, tree_sitter.Language):
                    logger.info("Converting PyCapsule to Language object")
                    try:
                        lang = tree_sitter.Language(language_capsule)
                        logger.info("✓ Successfully converted to Language object")
                    except Exception as e:
                        logger.error(f"✗ Failed to convert to Language object: {e}")
                        # Use capsule directly as fallback
                        lang = language_capsule
                else:
                    lang = language_capsule
                
                # Try setting language in parser
                try:
                    # Check if parser has set_language method or language attribute
                    if hasattr(parser, 'set_language'):
                        logger.info("Using parser.set_language() method")
                        parser.set_language(lang)
                    elif hasattr(parser, 'language'):
                        logger.info("Using parser.language attribute")
                        parser.language = lang
                    else:
                        logger.error("Parser has no method to set language!")
                        raise AttributeError("Parser has neither set_language method nor language attribute")
                    
                    logger.info("✓ Successfully set Java language in parser")
                    
                    # Test simple parse
                    source_code = b"public class Test { }"
                    tree = parser.parse(source_code)
                    logger.info("✓ Successfully parsed a simple Java class")
                    logger.info(f"  - Root node type: {tree.root_node.type}")
                    
                    return True
                except Exception as e:
                    logger.error(f"✗ Failed to set language in parser: {e}")
            except Exception as e:
                logger.error(f"✗ tree-sitter-java.language() execution failed: {e}")
        else:
            logger.error("✗ tree-sitter-java.language() function not found!")
    except ImportError:
        logger.error("✗ tree-sitter-java package not found!")
    
    return False

if __name__ == "__main__":
    success = check_tree_sitter()
    if success:
        logger.info("All checks passed! tree-sitter is correctly configured for Java parsing.")
        sys.exit(0)
    else:
        logger.error("Some checks failed. See log above for details.")
        sys.exit(1) 