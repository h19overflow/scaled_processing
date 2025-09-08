"""
Preference manager for user-customized extractions.
Applies user preferences to extraction schemas and prompts.
"""

import logging
from typing import Dict, Any, Optional

from src.backend.doc_processing_system.core_deps.database.CRUD.preferences_crud import PreferencesCRUD
from src.backend.doc_processing_system.core_deps.database.connection_manager import ConnectionManager


# Integration with LLM prompt templates verified - using generate_preference_prompt_injection()
# Field enhancement automation handled through apply_preferences_to_schema() method

class PreferenceManager:
    """Core logic for user preference management."""

    def __init__(self, connection_manager: ConnectionManager):
        """Initialize preference manager."""
        self.connection_manager = connection_manager
        self.preferences_crud = PreferencesCRUD(connection_manager)
        self.logger = logging.getLogger(__name__)

    async def get_user_preferences(
            self,
            user_id: str,
            classification: str
    ) -> Dict[str, Any]:
        """Load user preferences for specific document type."""
        try:
            preferences_record = self.preferences_crud.get_user_preferences(
                user_id=user_id,
                classification=classification
            )

            if preferences_record:
                return {
                    "field_preferences": preferences_record.field_preferences,
                    "extraction_style": preferences_record.extraction_style,
                    "prompt_instructions": preferences_record.prompt_instructions
                }
            else:
                # Return default preferences
                defaults = self.preferences_crud.get_default_preferences()
                return defaults

        except Exception as e:
            self.logger.error(f"Failed to get user preferences: {e}")
            return self.preferences_crud.get_default_preferences()

    # TODO investigate behaviour with schema generation.
    async def apply_preferences_to_schema(
            self,
            schema: Dict[str, Any],
            preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Modify extraction schema based on user preferences."""
        try:
            modified_schema = schema.copy()
            field_preferences = preferences.get("field_preferences", {})

            # Apply field priorities
            field_priorities = field_preferences.get("field_priorities", {})
            if field_priorities and "fields" in modified_schema:
                for field in modified_schema["fields"]:
                    field_name = field.get("field_name", "")
                    if field_name in field_priorities:
                        priority_settings = field_priorities[field_name]

                        # Update field requirements
                        if "required" in priority_settings:
                            field["is_required"] = priority_settings["required"]

                        # Update field weight/priority
                        if "weight" in priority_settings:
                            field["priority"] = priority_settings["weight"]

                        # Update extraction style for field
                        if "extraction_style" in priority_settings:
                            field["extraction_style"] = priority_settings["extraction_style"]

            # Apply field mappings
            field_mappings = field_preferences.get("field_mappings", {})
            if field_mappings:
                modified_schema["field_mappings"] = field_mappings

            # Apply extraction rules
            extraction_rules = field_preferences.get("extraction_rules", {})
            if extraction_rules:
                modified_schema["extraction_rules"] = extraction_rules

            return modified_schema

        except Exception as e:
            self.logger.error(f"Failed to apply preferences to schema: {e}")
            return schema

    def generate_preference_prompt_injection(self, preferences: Dict[str, Any]) -> str:
        """Generate prompt text to inject user preferences."""
        try:
            prompt_parts = []

            # Add custom instructions
            prompt_instructions = preferences.get("prompt_instructions", "")
            if prompt_instructions:
                prompt_parts.append(f"Special instructions: {prompt_instructions}")

            # Add extraction style preferences
            extraction_style = preferences.get("extraction_style", {})
            if extraction_style:
                style_parts = []

                verbosity = extraction_style.get("verbosity", "standard")
                style_parts.append(f"Use {verbosity} verbosity")

                format_pref = extraction_style.get("format_preference", "structured")
                style_parts.append(f"format as {format_pref}")

                confidence_threshold = extraction_style.get("confidence_threshold", 0.7)
                style_parts.append(f"minimum confidence {confidence_threshold}")

                if extraction_style.get("context_awareness", True):
                    style_parts.append("use document context")

                if extraction_style.get("cross_reference", True):
                    style_parts.append("cross-reference fields for consistency")

                prompt_parts.append("Extraction preferences: " + ", ".join(style_parts))

            # Add field-specific preferences
            field_preferences = preferences.get("field_preferences", {})
            field_priorities = field_preferences.get("field_priorities", {})

            if field_priorities:
                high_priority_fields = [
                    field for field, settings in field_priorities.items()
                    if settings.get("weight", 0) >= 0.8
                ]

                if high_priority_fields:
                    prompt_parts.append(f"Focus especially on: {', '.join(high_priority_fields)}")

            # Add output formatting preferences
            output_formatting = extraction_style.get("output_formatting", {})
            if output_formatting:
                format_parts = []
                for format_type, format_style in output_formatting.items():
                    format_parts.append(f"{format_type}: {format_style}")

                if format_parts:
                    prompt_parts.append(f"Format output with: {', '.join(format_parts)}")

            return "\n".join(prompt_parts) if prompt_parts else ""

        except Exception as e:
            self.logger.error(f"Failed to generate preference prompt: {e}")
            return ""

    async def save_user_preferences(
            self,
            user_id: str,
            classification: str,
            field_preferences: Optional[Dict[str, Any]] = None,
            extraction_style: Optional[Dict[str, Any]] = None,
            prompt_instructions: Optional[str] = None
    ) -> bool:
        """Save or update user preferences."""
        try:
            preferences_record = self.preferences_crud.create_or_update_preferences(
                user_id=user_id,
                classification=classification,
                field_preferences=field_preferences,
                extraction_style=extraction_style,
                prompt_instructions=prompt_instructions
            )

            if preferences_record:
                self.logger.info(f"Preferences saved for user {user_id}, classification {classification}")
                return True
            else:
                return False

        except Exception as e:
            self.logger.error(f"Failed to save preferences: {e}")
            return False

    def get_all_user_preferences(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        """Get all preferences for a user, organized by classification."""
        try:
            preferences_records = self.preferences_crud.get_all_user_preferences(user_id)

            result = {}
            for record in preferences_records:
                result[record.classification] = {
                    "field_preferences": record.field_preferences,
                    "extraction_style": record.extraction_style,
                    "prompt_instructions": record.prompt_instructions,
                    "updated_at": record.updated_at.isoformat() if record.updated_at else None
                }

            return result

        except Exception as e:
            self.logger.error(f"Failed to get all user preferences: {e}")
            return {}
