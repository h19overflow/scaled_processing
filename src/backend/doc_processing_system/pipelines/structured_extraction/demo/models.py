"""
Shared data models for the multi-agent extraction system.
Contains all Pydantic models used across components.
"""

from typing import List
from pydantic import BaseModel

class FieldSchema(BaseModel):
    """Schema for a single extractable field."""
    field_name: str
    field_type: str 
    description: str
    example_text: str
    category: str
    subcategory: str = "general"

class DocumentSchema(BaseModel):
    """Complete schema for document extraction."""
    document_type: str
    extraction_classes: List[FieldSchema]
    extraction_prompt: str