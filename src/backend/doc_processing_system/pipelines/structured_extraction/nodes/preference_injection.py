"""
User preference injection node for enhanced extraction pipeline.
"""

import logging
from typing import Dict, Any

from ..models.state import MultiAgentState
from ..services.preference_manager import PreferenceManager
from ....core_deps.database.connection_manager import ConnectionManager


async def inject_user_preferences(state: MultiAgentState) -> Dict[str, Any]:
    """Load and inject user preferences into extraction process."""
    logger = logging.getLogger(__name__)

    try:
        # Get required state
        classification = state.get("classification", "unknown")
        user_id = state.get("user_id", "default_user")

        if classification == "unknown":
            logger.warning("No classification available for preference injection")
            return {
                **state,
                "user_preferences": {},
                "status": "preference_injection_skipped"
            }

        # Initialize preference manager
        connection_manager = ConnectionManager()
        preference_manager = PreferenceManager(connection_manager)

        # Load user preferences
        logger.info(f"Loading preferences for {classification}")
        user_preferences = preference_manager.get_user_preferences(
            user_id=user_id,
            classification=classification
        )
        updated_state = {
            "user_preferences": user_preferences,
            "status": "preferences_loaded"
        }

        has_custom = bool(user_preferences.get("prompt_instructions"))
        logger.info(f"Loaded preferences (custom instructions: {has_custom})")

        return updated_state

    except Exception as e:
        logger.error(f"Preference injection failed: {e}")
        return {
            **state,
            "user_preferences": {},
            "status": "preference_injection_failed",
            "error": str(e)
        }
