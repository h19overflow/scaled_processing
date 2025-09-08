"""
Feedback context manager for structured extraction enhancements.
Loads and applies user feedback to improve extractions.
"""

import logging
from typing import Dict, List, Any, Optional

from ...core_deps.database.CRUD.feedback_crud import FeedbackCRUD
from ...core_deps.database.connection_manager import ConnectionManager


class FeedbackContextManager:
    """Core logic for managing feedback context in extractions."""

    def __init__(self, connection_manager: ConnectionManager):
        """Initialize feedback context manager."""
        self.connection_manager = connection_manager
        self.feedback_crud = FeedbackCRUD(connection_manager)
        self.logger = logging.getLogger(__name__)

    async def get_feedback_context(
            self,
            classification: str,
            user_id: str,
            limit: int = 5
    ) -> Dict[str, Any]:
        """Get relevant feedback context for enhancement."""
        try:
            # Get top-rated feedback for this document type
            feedback_records = self.feedback_crud.get_feedback_by_classification(
                classification=classification,
                user_id=user_id,
                limit=limit
            )

            if not feedback_records:
                return {
                    "relevant_feedback": [],
                    "context_prompt": "",
                    "field_corrections": {},
                    "common_issues": []
                }

            # Extract feedback data
            relevant_feedback = []
            field_corrections = {}
            common_issues = []

            for feedback in feedback_records:
                feedback_data = {
                    "rating": feedback.feedback_rating,
                    "comment": feedback.feedback_comment,
                    "fields": feedback.extraction_fields,
                    "type": feedback.feedback_type
                }
                relevant_feedback.append(feedback_data)

                # Collect field corrections
                if feedback.extraction_fields:
                    for field_name, field_data in feedback.extraction_fields.items():
                        if isinstance(field_data, dict) and "correction" in field_data:
                            if field_name not in field_corrections:
                                field_corrections[field_name] = []
                            field_corrections[field_name].append(field_data["correction"])

                # Collect common issues
                if feedback.feedback_comment:
                    common_issues.append(feedback.feedback_comment)

            # Build context prompt
            context_prompt = self.build_enhancement_prompt(relevant_feedback, field_corrections)

            return {
                "relevant_feedback": relevant_feedback,
                "context_prompt": context_prompt,
                "field_corrections": field_corrections,
                "common_issues": common_issues[:3]  # Top 3 issues
            }

        except Exception as e:
            self.logger.error(f"Failed to get feedback context: {e}")
            return {
                "relevant_feedback": [],
                "context_prompt": "",
                "field_corrections": {},
                "common_issues": []
            }

    def build_enhancement_prompt(
            self,
            feedback_data: List[Dict[str, Any]],
            field_corrections: Dict[str, List[str]]
    ) -> str:
        """Generate prompt enhancement based on feedback."""
        if not feedback_data:
            return ""

        prompt_parts = ["Based on previous user feedback, please pay special attention to:"]

        # Add field correction guidance
        if field_corrections:
            prompt_parts.append("\nField-specific corrections:")
            for field_name, corrections in field_corrections.items():
                unique_corrections = list(set(corrections))
                if unique_corrections:
                    prompt_parts.append(f"- {field_name}: {', '.join(unique_corrections[:2])}")

        # Add general feedback insights
        high_rated_comments = [
            f["comment"] for f in feedback_data
            if f.get("rating", 0) >= 4 and f.get("comment")
        ]

        if high_rated_comments:
            prompt_parts.append("\nPrevious successful approaches:")
            for comment in high_rated_comments[:2]:
                prompt_parts.append(f"- {comment}")

        return "\n".join(prompt_parts)

    async def capture_feedback(
            self,
            document_id: str,
            user_id: str,
            feedback_data: Dict[str, Any]
    ) -> bool:
        """Store user feedback with field-level details."""
        try:
            feedback_record = self.feedback_crud.create_feedback(
                document_id=document_id,
                user_id=user_id,
                classification=feedback_data.get("classification", "unknown"),
                feedback_type=feedback_data.get("type", "general"),
                feedback_rating=feedback_data.get("rating"),
                feedback_comment=feedback_data.get("comment"),
                extraction_fields=feedback_data.get("fields", {}),
                system_generated=feedback_data.get("system_generated", False)
            )

            if feedback_record:
                self.logger.info(f"Feedback captured for document {document_id}")
                return True
            else:
                return False

        except Exception as e:
            self.logger.error(f"Failed to capture feedback: {e}")
            return False

    def get_document_feedback(self, document_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Get all feedback for a specific document."""
        try:
            feedback_records = self.feedback_crud.get_feedback_by_document(
                document_id=document_id,
                user_id=user_id
            )

            return [
                {
                    "id": str(record.id),
                    "rating": record.feedback_rating,
                    "comment": record.feedback_comment,
                    "type": record.feedback_type,
                    "fields": record.extraction_fields,
                    "created_at": record.created_at.isoformat() if record.created_at else None
                }
                for record in feedback_records
            ]

        except Exception as e:
            self.logger.error(f"Failed to get document feedback: {e}")
            return []
