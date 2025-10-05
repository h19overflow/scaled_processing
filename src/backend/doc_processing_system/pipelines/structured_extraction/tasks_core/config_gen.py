"""
Configuration generation node using config_router for classification-based prompts and examples.
"""

try:
    import langextract as lx
    LANGEXTRACT_AVAILABLE = True
except ImportError:
    LANGEXTRACT_AVAILABLE = False

from ..models.state import PipelineState
from ..utils.config_router import process_document
from prefect import task
from typing import Any
import logging

logger = logging.getLogger(__name__)

@task(name="config-generation",
      retries=2,
      retry_delay_seconds=10,
      description="Generate extraction configuration and extract structured information from document.")
def generate_config(state: PipelineState) -> dict[str, Any] | None:
    """Generate extraction configuration using config_router based on document classification."""
    try:
        # Get document classification
        classification = getattr(state, "classification", "unknown")
        
        if classification == "unknown":
            raise ValueError("Document classification is unknown - cannot generate appropriate config")
        
        document_text = getattr(state, 'document_text', None)
        if not document_text:
            logger.error("No document text available for extraction")
            return {
                'extractions': [],
                'status': 'config_generation_failed',
                'error': 'No document text available'
            }
        
        # Process document using PydanticAI config_router
        result = process_document(document_text)
        
        # Handle the new PydanticAI return format
        if isinstance(result, dict):
            if result.get('status') == 'completed':
                logger.info(f"✅ Extraction completed successfully with {result.get('total_extractions', 0)} extractions")
                # Use state's document_id, not the result's (which is always None from config_router)
                document_id = getattr(state, 'document_id', None)
                logger.info(f"📋 Using document_id from state: {document_id}")
                return {
                    'extractions': result.get('extractions', []),
                    'document_id': document_id,
                    'status': 'config_generation_completed',
                    'total_extractions': result.get('total_extractions', 0)
                }
            else:
                logger.error(f"Extraction failed: {result.get('error', 'Unknown error')}")
                return {
                    'extractions': [],
                    'status': 'config_generation_failed',
                    'error': result.get('error', 'Extraction failed'),
                    'total_extractions': 0
                }
        
        # Fallback for unexpected result format
        logger.error(f"Unexpected result format from process_document: {type(result)}")
        return {
            'extractions': [],
            'status': 'config_generation_failed',
            'error': f'Unexpected result format: {type(result)}',
            'total_extractions': 0
        }

    except Exception as e:
        logger.error(f"Error generating configuration: {e}")
        return {
            'extractions': [],
            'status': 'config_generation_failed', 
            'error': str(e),
            'total_extractions': 0
        }
