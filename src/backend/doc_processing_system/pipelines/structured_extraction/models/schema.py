"""
Schema-related models for structured extraction.
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


class ProgressiveSchema(BaseModel):
    """Schema that builds progressively across chunks."""
    discovered_fields: List[FieldSchema]
    document_type: str
    confidence_level: str
    chunk_coverage: int


class ConsolidatedSchema(BaseModel):
    """Final consolidated schema after merging and optimization."""
    final_fields: List[FieldSchema]
    document_type: str
    optimization_notes: str
    extraction_prompt: str
