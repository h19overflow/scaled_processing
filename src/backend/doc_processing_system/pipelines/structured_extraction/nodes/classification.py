"""
Document classification node for enhanced extraction pipeline.
"""

import logging
from typing import Dict, Any

from ..models.state import MultiAgentState
from ..services.classification_service import DocumentClassificationService
from ....core_deps.database.connection_manager import ConnectionManager


async def classify_document(state: MultiAgentState) -> Dict[str, Any]:
    """Classify document type using classification service."""
    logger = logging.getLogger(__name__)

    try:
        # Get required state
        document_text = state.get("document_text", "")
        document_id = state.get("document_id", "")
        user_id = state.get("user_id", "default_user")

        if not document_text or not document_id:
            logger.warning("Missing document text or ID for classification")
            return {
                **state,
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
            document_id=document_id,
            user_id=user_id
        )

        # Update state with classification results
        updated_state = {
            **state,
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
            **state,
            "classification": "unknown",
            "classification_confidence": 0.0,
            "status": "classification_failed",
            "error": str(e)
        }
