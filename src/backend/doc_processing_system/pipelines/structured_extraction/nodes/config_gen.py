"""
Configuration generation node using config_router for classification-based prompts and examples.
"""

try:
    import langextract as lx
    LANGEXTRACT_AVAILABLE = True
except ImportError:
    LANGEXTRACT_AVAILABLE = False

from ..models.state import PipelineState
from ..services.config_router import route_classification, process_document
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
        
        # Use config_router to get appropriate prompt and examples
        prompt, examples = route_classification(classification)
        
        if prompt == "Unknown classification":
            # Fallback to general extraction
            prompt = "Extract structured information from this document. Use exact text from the document for extractions."
            examples = []

        if getattr(state, 'document_text', None) and LANGEXTRACT_AVAILABLE:
            results = process_document(getattr(state, 'document_text'), prompt)


            return {'results':results}

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error generating configuration: {e}")

