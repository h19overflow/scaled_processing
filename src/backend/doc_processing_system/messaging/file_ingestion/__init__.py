"""
File ingestion messaging components.
Handles file detection and initial document processing triggers.
"""

from .file_processing_consumer import FileProcessingConsumer, create_file_processing_consumer

__all__ = [
    "FileProcessingConsumer",
    "create_file_processing_consumer"
]