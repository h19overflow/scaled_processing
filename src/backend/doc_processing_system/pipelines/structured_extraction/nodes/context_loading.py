"""
Feedback context loading node for enhanced extraction pipeline.
"""

import logging
from typing import Dict, Any

from ..models.state import MultiAgentState
from ..services.feedback_context_manager import FeedbackContextManager
from ....core_deps.database.connection_manager import ConnectionManager


async def load_feedback_context(state: MultiAgentState) -> Dict[str, Any]:
    """Load relevant feedback context for extraction enhancement."""
    logger = logging.getLogger(__name__)

    try:
        # Get required state
        classification = state.get("classification", "unknown")
        user_id = state.get("user_id", "default_user")

        if classification == "unknown":
            logger.warning("No classification available for context loading")
            return {
                **state,
                "feedback_context": {},
                "status": "context_loading_skipped"
            }

        # Initialize feedback context manager
        connection_manager = ConnectionManager()
        context_manager = FeedbackContextManager(connection_manager)

        # Load feedback context
        logger.info(f"Loading feedback context for {classification}")
        feedback_context = await context_manager.get_feedback_context(
            classification=classification,
            user_id=user_id,
            limit=5
        )

        # Update state with feedback context
        updated_state = {
            **state,
            "feedback_context": feedback_context,
            "status": "context_loaded"
        }

        context_items = len(feedback_context.get("relevant_feedback", []))
        logger.info(f"Loaded {context_items} feedback items for context")

        return updated_state

    except Exception as e:
        logger.error(f"Context loading failed: {e}")
        return {
            **state,
            "feedback_context": {},
            "status": "context_loading_failed",
            "error": str(e)
        }
