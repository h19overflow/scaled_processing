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
    """Model for extraction results from agents."""
    document_id: str
    page_range: Tuple[int, int]
    extracted_fields: Dict[str, Any]
    confidence_scores: Dict[str, float]
    agent_id: str
    timestamp: Optional[datetime] = None
    
    def get_data(self) -> Dict[str, Any]:
        """Get extracted data."""
        return self.extracted_fields
    
    def get_confidence(self) -> float:
        """Get average confidence score."""
        if not self.confidence_scores:
            return 0.0
        return sum(self.confidence_scores.values()) / len(self.confidence_scores)
    
    def is_valid(self) -> bool:
        """Check if extraction result is valid."""
        return (
            bool(self.document_id) and
            bool(self.extracted_fields) and
            self.get_confidence() > 0.5
        )
    
    def merge_with(self, other: 'ExtractionResult') -> 'ExtractionResult':
        """Merge with another extraction result."""
        if self.document_id != other.document_id:
            raise ValueError("Cannot merge results from different documents")
        
        merged_fields = {**self.extracted_fields, **other.extracted_fields}
        merged_confidence = {**self.confidence_scores, **other.confidence_scores}
        
        return ExtractionResult(
            document_id=self.document_id,
            page_range=(
                min(self.page_range[0], other.page_range[0]),
                max(self.page_range[1], other.page_range[1])
            ),
            extracted_fields=merged_fields,
            confidence_scores=merged_confidence,
            agent_id=f"{self.agent_id}+{other.agent_id}",
            timestamp=datetime.now()
        )


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