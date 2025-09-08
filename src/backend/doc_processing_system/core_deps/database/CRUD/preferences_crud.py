"""
CRUD operations for user preferences.
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .base_repository import BaseRepository
from ..models import UserPreferencesModel


class PreferencesCRUD(BaseRepository):
    """CRUD operations for user preferences."""

    def create_or_update_preferences(
            self,
            user_id: str,
            classification: str,
            field_preferences: Optional[Dict[str, Any]] = None,
            extraction_style: Optional[Dict[str, Any]] = None,
            prompt_instructions: Optional[str] = None
    ) -> Optional[UserPreferencesModel]:
        """Create or update user preferences for document type."""
        try:
            with self.connection_manager.get_session() as session:
                # Check if preferences exist
                existing = session.query(UserPreferencesModel).filter(
                    and_(
                        UserPreferencesModel.user_id == user_id,
                        UserPreferencesModel.classification == classification
                    )
                ).first()

                if existing:
                    # Update existing
                    if field_preferences is not None:
                        existing.field_preferences = field_preferences
                    if extraction_style is not None:
                        existing.extraction_style = extraction_style
                    if prompt_instructions is not None:
                        existing.prompt_instructions = prompt_instructions

                    session.commit()
                    session.refresh(existing)

                    self._log_operation("Updated preferences", str(existing.id))
                    return existing
                else:
                    # Create new
                    preferences = UserPreferencesModel(
                        user_id=user_id,
                        classification=classification,
                        field_preferences=field_preferences or {},
                        extraction_style=extraction_style or {},
                        prompt_instructions=prompt_instructions
                    )

                    session.add(preferences)
                    session.commit()
                    session.refresh(preferences)

                    self._log_operation("Created preferences", str(preferences.id))
                    return preferences

        except Exception as e:
            self.logger.error(f"Failed to create/update preferences: {e}")
            return None

    def get_user_preferences(
            self,
            user_id: str,
            classification: str
    ) -> Optional[UserPreferencesModel]:
        """Get user preferences for specific document type."""
        try:
            with self.connection_manager.get_session() as session:
                return session.query(UserPreferencesModel).filter(
                    and_(
                        UserPreferencesModel.user_id == user_id,
                        UserPreferencesModel.classification == classification
                    )
                ).first()

        except Exception as e:
            self.logger.error(f"Failed to get preferences: {e}")
            return None

    def get_all_user_preferences(self, user_id: str) -> list[UserPreferencesModel]:
        """Get all preferences for a user."""
        try:
            with self.connection_manager.get_session() as session:
                return session.query(UserPreferencesModel).filter(
                    UserPreferencesModel.user_id == user_id
                ).all()

        except Exception as e:
            self.logger.error(f"Failed to get all user preferences: {e}")
            return []

    def delete_preferences(self, user_id: str, classification: str) -> bool:
        """Delete user preferences for document type."""
        try:
            with self.connection_manager.get_session() as session:
                preferences = session.query(UserPreferencesModel).filter(
                    and_(
                        UserPreferencesModel.user_id == user_id,
                        UserPreferencesModel.classification == classification
                    )
                ).first()

                if not preferences:
                    return False

                session.delete(preferences)
                session.commit()

                self._log_operation("Deleted preferences", str(preferences.id))
                return True

        except Exception as e:
            self.logger.error(f"Failed to delete preferences: {e}")
            return False

    def get_default_preferences(self) -> Dict[str, Any]:
        """Get default preference structure."""
        return {
            "field_preferences": {
                "field_priorities": {},
                "field_mappings": {},
                "extraction_rules": {
                    "dates_format": "YYYY-MM-DD",
                    "currency_format": "USD",
                    "name_format": "full_legal_name"
                }
            },
            "extraction_style": {
                "verbosity": "standard",
                "format_preference": "structured",
                "language": "en",
                "confidence_threshold": 0.7,
                "context_awareness": True,
                "cross_reference": True,
                "fallback_behavior": "skip",
                "output_formatting": {
                    "dates": "ISO_8601",
                    "numbers": "with_separators",
                    "addresses": "single_line",
                    "phone_numbers": "international_format"
                }
            }
        }
