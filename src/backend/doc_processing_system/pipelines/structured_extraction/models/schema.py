"""
Schema-related models for structured extraction.
"""

from pydantic import BaseModel


class FieldSchema(BaseModel):
    """Schema for a single extractable field."""
    field_name: str
    field_type: str
    description: str
    example_text: str
    category: str
    subcategory: str = "general"





