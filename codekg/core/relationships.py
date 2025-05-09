"""
Core relationships for the Code Knowledge Graph.
"""
from typing import Optional, Dict, Any, Type
from pydantic import BaseModel, Field

from .entities import CodeResource


class Relationship(BaseModel):
    """Base class for all relationships."""
    
    source: str  # ID of source node
    target: str  # ID of target node
    type: str = Field(default_factory=lambda: "RELATIONSHIP")
    properties: Dict[str, Any] = Field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(source={self.source}, target={self.target})"


class DefinedIn(Relationship):
    """Indicates that a code entity is defined within a specific file."""
    
    type: str = Field(default="DEFINED_IN")
    line_number_start: Optional[int] = None
    line_number_end: Optional[int] = None
    column_number_start: Optional[int] = None
    column_number_end: Optional[int] = None


class Contains(Relationship):
    """Represents containment or membership."""
    
    type: str = Field(default="CONTAINS")


class Calls(Relationship):
    """Represents a function or method call."""
    
    type: str = Field(default="CALLS")
    line_number: Optional[int] = None
    is_dynamic_dispatch: Optional[bool] = None
    call_type: Optional[str] = None  # STATIC, VIRTUAL, INTERFACE, SUPER


class HasParameter(Relationship):
    """Links a Callable to its Parameters."""
    
    type: str = Field(default="HAS_PARAMETER")


class References(Relationship):
    """Indicates that a code entity refers to or uses a type definition."""
    
    type: str = Field(default="REFERENCES")
    usage_context: Optional[str] = None  # RETURN_TYPE, PARAMETER_TYPE, etc.


class Accesses(Relationship):
    """Represents access to a variable (read or write)."""
    
    type: str = Field(default="ACCESSES")
    access_type: str  # READ, WRITE, READ_WRITE
    line_number: Optional[int] = None


class InheritsFrom(Relationship):
    """Represents class inheritance."""
    
    type: str = Field(default="INHERITS_FROM")


class Implements(Relationship):
    """Represents a class implementing an interface."""
    
    type: str = Field(default="IMPLEMENTS")


class Imports(Relationship):
    """Represents a dependency where one code unit imports/includes/uses another."""
    
    type: str = Field(default="IMPORTS")
    alias: Optional[str] = None


class AnnotatedBy(Relationship):
    """Links a code element to an Annotation or Decorator that applies to it."""
    
    type: str = Field(default="ANNOTATED_BY")


class Throws(Relationship):
    """Indicates a Callable may throw a specific type of exception."""
    
    type: str = Field(default="THROWS")
    is_declared: bool = False


class CreatesInstance(Relationship):
    """Represents the instantiation of an object."""
    
    type: str = Field(default="CREATES_INSTANCE")
    line_number: Optional[int] = None


class AssociatedComment(Relationship):
    """Links a code entity to a relevant Comment."""
    
    type: str = Field(default="ASSOCIATED_COMMENT") 