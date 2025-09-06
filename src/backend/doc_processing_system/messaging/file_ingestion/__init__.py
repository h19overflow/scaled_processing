"""
File ingestion messaging components.
Handles file detection and initial document processing triggers.
"""

from .file_processing_consumer import FileProcessingConsumer

__all__ = [
    "FileProcessingConsumer",
]