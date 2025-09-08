"""
Document-related models for structured extraction.
"""

from typing import List, TYPE_CHECKING
from dataclasses import dataclass
from pydantic import BaseModel

if TYPE_CHECKING:
    from .schema import FieldSchema


@dataclass
class DocumentChunk:
    """A chunk of document with metadata."""
    chunk_id: int
    text: str
    start_char: int
    end_char: int
    token_count: int


class DocumentSchema(BaseModel):
    """Complete schema for document extraction."""
    document_type: str
    extraction_classes: List["FieldSchema"]
    extraction_prompt: str
