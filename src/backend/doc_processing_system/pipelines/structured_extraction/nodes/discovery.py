"""
Sequential schema discovery node.
"""

from typing import List
import os
import logging

from ..models.state import MultiAgentState
from ..models.schema import FieldSchema, ProgressiveSchema
from ..config.settings import Settings
from ..agents.discovery import create_discovery_agent, SequentialDiscoveryDeps
# TODO EXAMINE DISCOVERY AGENT's OUTPUTS , ENSURE IT ADHERES TO THE STATE SPECIFICATIONS
async def sequential_discovery(state: MultiAgentState, settings: Settings) -> MultiAgentState:
    """Process chunks sequentially to discover schemas."""
    logger = logging.getLogger(__name__)
    
    try:
        # Get context from state (populated by preference_injection and context_loading nodes)
        user_preferences = state.get("user_preferences", {})
        feedback_context = state.get("feedback_context", {})
        user_id = state.get("user_id", "default_user")
        classification = state.get("classification", "unknown")

        # Create agent
        agent = create_discovery_agent(settings.models.discovery_model)

        # Process chunks
        progressive_results = []
        discovered_fields: List[FieldSchema] = []
        document_type = settings.extraction.document_type

        logger.info(f"Starting discovery with preferences: {bool(user_preferences)} and feedback: {bool(feedback_context.get('relevant_feedback'))}")

        for chunk in state["chunks"]:
            deps = SequentialDiscoveryDeps(
                chunk_text=chunk.text,
                chunk_id=chunk.chunk_id,
                previous_discoveries=discovered_fields.copy(),
                document_type=document_type,
                user_preferences=user_preferences,
                feedback_context=feedback_context,
                user_id=user_id,
                classification=classification
            )

            result = await agent.run(
                f"Analyze chunk {chunk.chunk_id} and find new extractable fields",
                deps=deps
            )

            progressive_schema = result.data
            discovered_fields.extend(progressive_schema.discovered_fields)
            document_type = progressive_schema.document_type
            progressive_results.append(progressive_schema)

        logger.info(f"Discovery completed with {len(discovered_fields)} total fields discovered")
        return {
            **state,
            "progressive_results": progressive_results,
            "status": "discovery_complete"
        }

    except Exception as e:
        logger.error(f"Sequential discovery failed: {e}")
        # Fallback with basic fields
        fallback_results = _create_fallback_schema(state["chunks"])

        return {
            **state,
            "progressive_results": fallback_results,
            "error": f"Sequential discovery failed: {str(e)}",
            "status": "discovery_complete"
        }


def _create_fallback_schema(chunks) -> List[ProgressiveSchema]:
    """Create fallback schema when AI fails."""
    basic_fields = [
        FieldSchema(
            field_name="personal_info",
            field_type="contact",
            description="Name, email, phone, location",
            example_text="Personal contact information",
            category="identity",
            subcategory="contact"
        ),
        FieldSchema(
            field_name="skills",
            field_type="technical_skill",
            description="Technical skills and technologies",
            example_text="Programming languages and tools",
            category="technical",
            subcategory="programming"
        )
    ]

    return [
        ProgressiveSchema(
            discovered_fields=basic_fields if i == 0 else [],
            document_type="document",
            confidence_level="low",
            chunk_coverage=i + 1
        )
        for i in range(len(chunks))
    ]
