"""
Extraction-related data models for structured data extraction.
Contains models for field specifications, extraction results, and agent scaling.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
from pydantic import BaseModel


class FieldSpecification(BaseModel):
    """Model for field specification in extraction schema."""
    field_name: str
    field_type: str
    description: str
    validation_rules: Dict[str, Any] = {}
    is_required: bool = False


class FieldInitRequest(BaseModel):
    """Model for field initialization request."""
    document_id: str
    page_count: int
    sampling_strategy: str = "random"
    max_sample_pages: int = 5


class AgentScalingConfig(BaseModel):
    """Model for agent scaling configuration."""
    document_id: str
    page_count: int
    agent_count: int
    page_ranges: List[Tuple[int, int]]
    field_specs: List[FieldSpecification]


class ExtractionResult(BaseModel):
    """Model for structured document extraction results."""
    document_id: str
    extraction_class: str
    extraction_text: str
    attributes: Dict[str, Any]
    alignment_status: str
    extraction_index: int
    group_index: int
    description: Optional[str] = None
    char_start_pos: int
    char_end_pos: int
    timestamp: Optional[datetime] = None
    
    def get_data(self) -> Dict[str, Any]:
        """Get extracted attributes."""
        return self.attributes
    
    def get_text_length(self) -> int:
        """Get length of extracted text."""
        return self.char_end_pos - self.char_start_pos
    
    def is_valid(self) -> bool:
        """Check if extraction result is valid."""
        return (
            bool(self.document_id) and
            bool(self.extraction_class) and
            bool(self.extraction_text) and
            self.char_end_pos > self.char_start_pos
        )
    
    def is_aligned(self) -> bool:
        """Check if extraction is properly aligned."""
        return self.alignment_status in ["match_exact", "match_fuzzy"]


class ExtractionSchema(BaseModel):
    """Model for extraction schema containing field specifications."""
    fields: List[FieldSpecification]
    validation_rules: Dict[str, Any] = {}
    created_by: str = "system"
    created_at: Optional[datetime] = None
    
    def get_fields(self) -> List[FieldSpecification]:
        """Get field specifications."""
        return self.fields
    
    def add_field(self, field: FieldSpecification) -> bool:
        """Add a field specification."""
        try:
            self.fields.append(field)
            return True
        except Exception:
            return False
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate data against schema."""
        required_fields = [f.field_name for f in self.fields if f.is_required]
        return all(field in data for field in required_fields)
    
    def to_json(self) -> str:
        """Convert schema to JSON string."""
        return self.json()