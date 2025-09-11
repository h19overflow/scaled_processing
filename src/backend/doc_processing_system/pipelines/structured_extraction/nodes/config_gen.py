"""
Configuration generation node using config_router for classification-based prompts and examples.
"""

try:
    import langextract as lx
    LANGEXTRACT_AVAILABLE = True
except ImportError:
    LANGEXTRACT_AVAILABLE = False

from ..models.state import PipelineState
from ..services.config_router import  process_document
from prefect import task
from typing import  Any

@task(name="config-generation",
      retries=2,
      retry_delay_seconds=10,
      description="Generate langextract configuration, and extract structured information from document.")
def generate_config(state: PipelineState) -> dict[str, Any] | None:
    """Generate langextract configuration using config_router based on document classification."""
    try:
        # Get document classification
        classification = getattr(state, "classification", "unknown")
        
        if classification == "unknown":
            raise ValueError("Document classification is unknown - cannot generate appropriate config")
        
        if getattr(state, 'document_text', None) and LANGEXTRACT_AVAILABLE:
            # Pass classification directly to process_document - it will handle routing internally
            results = process_document(getattr(state, 'document_text'), classification)


            return {'results':results}

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error generating configuration: {e}")

