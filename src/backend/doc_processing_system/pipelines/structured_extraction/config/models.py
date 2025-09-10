"""
Configuration validation models.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ChunkingConfig(BaseModel):
    """Configuration for document chunking."""
    max_tokens: int = Field(default=1500, ge=100, le=4000)
    overlap_tokens: int = Field(default=200, ge=0, le=500)
    use_tiktoken: bool = True


class ModelConfig(BaseModel):
    """Configuration for AI models."""
    discovery_model: str = "gemini-2.0-flash"
    extraction_model: str = "gemini-2.0-flash"
    openai_api_key: Optional[str] = None


class ExtractionConfig(BaseModel):
    """Configuration for extraction process."""
    max_fields: int = Field(default=8, ge=1, le=20)
    document_type: str = "unknown"
    output_dir: str = "demo_results"
