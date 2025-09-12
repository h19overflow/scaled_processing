"""
Document classification node for enhanced extraction pipeline.
"""

import logging
from typing import Dict, Any

from ..models.state import PipelineState
from ..services.classification_service import DocumentClassificationService
from ....core_deps.database.connection_manager import ConnectionManager
from prefect import task


@task(name="document-classification",
      retries=2,
      retry_delay_seconds=10,
      description="Classify document type using classification service."
      )

async def classify_document(state: PipelineState) -> Dict[str, Any]:
    """Classify document type using classification service."""
    logger = logging.getLogger(__name__)

    try:
        # Get required state
        document_text = getattr(state, "document_text", "") or ""
        document_id = getattr(state, "document_id", "") or ""

        if not document_text or not document_id:
            logger.warning("Missing document text or ID for classification")
            return {
                "document_id": document_id,
                "classification": "unknown",
                "classification_confidence": 0.0,
                "status": "classification_failed"
            }

        # Initialize classification service
        connection_manager = ConnectionManager()
        classification_service = DocumentClassificationService(connection_manager)

        # Perform classification
        logger.info(f"Classifying document {document_id}")
        classification_result = await classification_service.classify_document(
            document_text=document_text,
        )

        # Update state with classification results
        updated_state = {
            "classification": classification_result["classification"],
            "classification_confidence": classification_result["confidence"],
            "status": "classified"
        }

        logger.info(
            f"Document classified as '{classification_result['classification']}' "
            f"with confidence {classification_result['confidence']:.2f}"
        )

        return updated_state

    except Exception as e:
        logger.error(f"Classification failed: {e}")
        return {
            "classification": "unknown",
            "classification_confidence": 0.0,
            "status": "classification_failed",
            "error": str(e)
        }
