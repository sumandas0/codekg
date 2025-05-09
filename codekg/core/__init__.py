"""
Core module for CodeKG entities and relationships.
"""

from .knowledge_graph import CodeKnowledgeGraph
from .entities import (
    CodeResource,
    File,
    Namespace,
    Structure,
    Callable,
    Parameter,
    Variable,
    Annotation,
    Comment
)
from .relationships import (
    Relationship,
    DefinedIn,
    Contains,
    Calls,
    HasParameter,
    References,
    Accesses,
    InheritsFrom,
    Implements,
    Imports,
    AnnotatedBy,
    Throws,
    CreatesInstance,
    AssociatedComment
)

__all__ = [
    "CodeKnowledgeGraph",
    "CodeResource",
    "File",
    "Namespace",
    "Structure",
    "Callable",
    "Parameter",
    "Variable",
    "Annotation",
    "Comment",
    "Relationship",
    "DefinedIn",
    "Contains",
    "Calls",
    "HasParameter",
    "References",
    "Accesses",
    "InheritsFrom",
    "Implements",
    "Imports",
    "AnnotatedBy",
    "Throws",
    "CreatesInstance",
    "AssociatedComment"
] 