"""Configuration for vision processing components."""

from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class VisionConfig:
    """Configuration for vision processing pipeline."""
    
    # Model settings
    model_name: str = "gemini-2.5-flash-image-preview"
    
    # Concurrency settings
    classification_concurrency: int = 10
    analysis_concurrency: int = 3
    
    # Token limits
    classification_max_tokens: int = 10
    analysis_max_tokens: int = 500
    
    # Classification prompt (minimal tokens)
    classification_prompt: str = """Classify this document image. Context: {context}

Reply with exactly: ACTION confidence
- ANALYZE: Charts, graphs, diagrams, technical content, text
- SKIP: Logos, decorative, pure photos, UI screenshots

Example: ANALYZE 0.9"""
    
    # Analysis prompt (detailed)
    analysis_prompt: str = """Analyze this document image in detail. Context: {context}

Describe:
- Key information, data, insights
- Readable text content
- Relationship to document
- Technical details

Be thorough but concise."""
    
    # Feature flags
    enable_vision_processing: bool = True
    enable_classification_filter: bool = True
    
    @classmethod
    def from_env(cls) -> 'VisionConfig':
        """Create config from environment variables."""
        return cls(
            model_name=os.getenv('VISION_MODEL_NAME', cls.model_name),
            classification_concurrency=int(os.getenv('VISION_CLASSIFICATION_CONCURRENCY', cls.classification_concurrency)),
            analysis_concurrency=int(os.getenv('VISION_ANALYSIS_CONCURRENCY', cls.analysis_concurrency)),
            enable_vision_processing=os.getenv('ENABLE_VISION_PROCESSING', 'true').lower() == 'true',
            enable_classification_filter=os.getenv('ENABLE_VISION_CLASSIFICATION', 'true').lower() == 'true',
        )