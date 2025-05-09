"""
Core entities for the Code Knowledge Graph.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class CodeResource(BaseModel):
    """Base class for all code resources."""
    
    id: str
    name: str
    qualified_name: str
    documentation: Optional[str] = None
    language: Optional[str] = None

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, qualified_name={self.qualified_name})"
    
    def __hash__(self) -> int:
        return hash(self.qualified_name)
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, CodeResource):
            return False
        return self.qualified_name == other.qualified_name


class File(CodeResource):
    """Represents a physical file in the codebase."""
    
    path: str
    size: Optional[int] = None
    last_modified_date: Optional[datetime] = None
    checksum: Optional[str] = None


class Namespace(CodeResource):
    """Represents a logical grouping of code, such as a module, package, or namespace."""
    
    pass


class Structure(CodeResource):
    """Represents a user-defined type or data structure (class, struct, interface, enum)."""
    
    access_modifier: Optional[str] = None
    is_abstract: Optional[bool] = False
    is_interface: Optional[bool] = False


class Callable(CodeResource):
    """Represents an executable unit of code (function, method, constructor, lambda)."""
    
    return_type: Optional[str] = None
    access_modifier: Optional[str] = None
    is_static: Optional[bool] = False
    is_abstract: Optional[bool] = False
    cyclomatic_complexity: Optional[int] = None
    lines_of_code: Optional[int] = None
    signature: Optional[str] = None


class Parameter(CodeResource):
    """Represents a parameter of a Callable."""
    
    type: str
    default_value: Optional[str] = None
    position: int


class Variable(CodeResource):
    """Represents a variable (local, field, global)."""
    
    type: str
    initial_value: Optional[str] = None
    is_constant: Optional[bool] = False
    access_modifier: Optional[str] = None


class Annotation(CodeResource):
    """Represents metadata attached to code elements (annotations, decorators)."""
    
    parameters: Optional[Dict[str, str]] = Field(default_factory=dict)


class Comment:
    """Represents a code comment not directly part of formal documentation."""
    
    text: str
    type: str  # LINE, BLOCK, DOC
    line_number_start: int
    line_number_end: int 