"""
Schema-related models for structured extraction.
"""

from typing import List, Literal
from pydantic import BaseModel, Field


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


class DocumentClassificationResult(BaseModel):
    """Document classification result with structured output."""

    classification: Literal[
        "contract",
        "invoice",
        "resume",
        "legal",
        "medical",
        "attendance",
        "report",
        "other"
    ] = Field(
        description="The document classification category"
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0"
    )

    reasoning: str = Field(
        description="Brief explanation of why this classification was chosen"
    )

    keywords_found: List[str] = Field(
        default_factory=list,
        description="Key terms or phrases that influenced the classification"
    )
