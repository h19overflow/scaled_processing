"""
Main configuration class for structured extraction demo.
"""

import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from .models import ModelConfig, ExtractionConfig

load_dotenv()


class Settings(BaseModel):
    """Main settings for structured extraction workflow."""

    models: ModelConfig = Field(default_factory=ModelConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)

    def __init__(self, **data):
        """Initialize settings with environment variable defaults."""
        super().__init__(**data)

        # Set API key from environment if not provided
        if self.models.openai_api_key is None:
            self.models.openai_api_key = os.getenv("OPENAI_API_KEY", "")

    @classmethod
    def create_default(cls) -> "Settings":
        """Create settings with sensible defaults."""
        return cls()

    def get_output_path(self, filename: str) -> Path:
        """Get full output path for a filename."""
        output_dir = Path(self.extraction.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / filename
