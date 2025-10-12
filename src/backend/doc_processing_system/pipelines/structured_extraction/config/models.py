"""
Configuration validation models.
"""

from typing import Optional
from pydantic import BaseModel, Field




class ModelConfig(BaseModel):
    """Configuration for AI models."""
    discovery_model: str = "gemini-2.0-flash"
    extraction_model: str = "gemini-2.5-flash"
    openai_api_key: Optional[str] = None


class ExtractionConfig(BaseModel):
    """Configuration for extraction process."""
    max_fields: int = Field(default=8, ge=1, le=20)
    document_type: str = "unknown"
    output_dir: str = "demo_results"
