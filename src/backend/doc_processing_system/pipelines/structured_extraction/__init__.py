"""
Structured extraction pipeline with modular architecture.

Core components for orchestrating multi-agent document extraction with
template-based field definition and document classification.
"""

from src.backend.doc_processing_system.pipelines.structured_extraction.utils.classification_service import DocumentClassificationService
from src.backend.doc_processing_system.pipelines.structured_extraction.flows.prefect_flow import structured_extraction_flow

__all__ = [
    "DocumentClassificationService",
    "structured_extraction_flow",
]

