"""
Serialization strategies for document processing components.
Defines how tables and images should be serialized during document processing.
"""

from enum import Enum


class SerializationStrategy(Enum):
    """Serialization strategies for tables and images."""
    DEFAULT = "default"
    STRUCTURED = "structured"
    MARKDOWN = "markdown"
    JSON = "json"
    DETAILED = "detailed"
