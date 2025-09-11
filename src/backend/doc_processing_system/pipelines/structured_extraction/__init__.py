"""
Structured extraction pipeline with modular architecture.

Core components for orchestrating multi-agent document extraction with
template-based field definition and document classification.
"""

from .core.prefect_tasks import structured_extraction_flow
from .services.classification_service import DocumentClassificationService
from .services.field_template_manager import FieldTemplateManager

__all__ = [
    "structured_extraction_flow",
    "DocumentClassificationService",
    "FieldTemplateManager"
]
