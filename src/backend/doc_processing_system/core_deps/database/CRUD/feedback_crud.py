"""
CRUD operations for document feedback.
"""

from typing import List, Optional, Dict, Any

from sqlalchemy import and_, desc

from .base_repository import BaseRepository
from ..models import DocumentFeedbackModel


class FeedbackCRUD(BaseRepository):
    """CRUD operations for document feedback."""

    def create_feedback(
            self,
            document_id: str,
            user_id: str,
            classification: str,
            feedback_type: str,
            feedback_rating: Optional[int] = None,
            feedback_comment: Optional[str] = None,
            extraction_fields: Optional[Dict[str, Any]] = None,
            system_generated: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Create new document feedback."""
        try:
            with self.connection_manager.get_session() as session:
                feedback = DocumentFeedbackModel(
                    document_id=self._validate_uuid(document_id),
                    user_id=user_id,
                    classification=classification,
                    feedback_type=feedback_type,
                    feedback_rating=feedback_rating,
                    feedback_comment=feedback_comment,
                    extraction_fields=extraction_fields or {},
                    system_generated=system_generated
                )

                session.add(feedback)
                session.commit()
                session.refresh(feedback)

                self._log_operation("Created feedback", str(feedback.id))
                return {
                    "id": str(feedback.id),
                    "document_id": str(feedback.document_id),
                    "user_id": feedback.user_id,
                    "classification": feedback.classification,
                    "feedback_type": feedback.feedback_type,
                    "feedback_rating": feedback.feedback_rating,
                    "feedback_comment": feedback.feedback_comment,
                    "extraction_fields": feedback.extraction_fields or {},
                    "system_generated": feedback.system_generated,
                    "created_at": feedback.created_at.isoformat() if feedback.created_at else None
                }

        except Exception as e:
            self.logger.error(f"Failed to create feedback: {e}")
            return None

    def get_feedback_by_document(
            self,
            document_id: str,
            user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get feedback for a specific document."""
        try:
            with self.connection_manager.get_session() as session:
                query = session.query(DocumentFeedbackModel).filter(
                    DocumentFeedbackModel.document_id == self._validate_uuid(document_id)
                )

                if user_id:
                    query = query.filter(DocumentFeedbackModel.user_id == user_id)

                records = query.order_by(desc(DocumentFeedbackModel.created_at)).all()
                
                result = []
                for record in records:
                    result.append({
                        "id": str(record.id),
                        "document_id": str(record.document_id),
                        "user_id": record.user_id,
                        "classification": record.classification,
                        "feedback_type": record.feedback_type,
                        "feedback_rating": record.feedback_rating,
                        "feedback_comment": record.feedback_comment,
                        "extraction_fields": record.extraction_fields or {},
                        "system_generated": record.system_generated,
                        "created_at": record.created_at.isoformat() if record.created_at else None
                    })
                
                return result

        except Exception as e:
            self.logger.error(f"Failed to get feedback by document: {e}")
            return []

    def get_feedback_by_classification(
            self,
            classification: str,
            user_id: str,
            limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top-rated feedback for document classification."""
        try:
            with self.connection_manager.get_session() as session:
                records = session.query(DocumentFeedbackModel).filter(
                    and_(
                        DocumentFeedbackModel.classification == classification,
                        DocumentFeedbackModel.user_id == user_id,
                        DocumentFeedbackModel.feedback_rating.isnot(None)
                    )
                ).order_by(
                    desc(DocumentFeedbackModel.feedback_rating),
                    desc(DocumentFeedbackModel.created_at)
                ).limit(limit).all()
                
                result = []
                for record in records:
                    result.append({
                        "id": str(record.id),
                        "document_id": str(record.document_id),
                        "user_id": record.user_id,
                        "classification": record.classification,
                        "feedback_type": record.feedback_type,
                        "feedback_rating": record.feedback_rating,
                        "feedback_comment": record.feedback_comment,
                        "extraction_fields": record.extraction_fields or {},
                        "system_generated": record.system_generated,
                        "created_at": record.created_at.isoformat() if record.created_at else None
                    })
                
                return result

        except Exception as e:
            self.logger.error(f"Failed to get feedback by classification: {e}")
            return []

    def update_feedback(
            self,
            feedback_id: str,
            feedback_rating: Optional[int] = None,
            feedback_comment: Optional[str] = None,
            extraction_fields: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update existing feedback."""
        try:
            with self.connection_manager.get_session() as session:
                feedback = session.query(DocumentFeedbackModel).filter(
                    DocumentFeedbackModel.id == self._validate_uuid(feedback_id)
                ).first()

                if not feedback:
                    return False

                if feedback_rating is not None:
                    feedback.feedback_rating = feedback_rating
                if feedback_comment is not None:
                    feedback.feedback_comment = feedback_comment
                if extraction_fields is not None:
                    feedback.extraction_fields = extraction_fields

                session.commit()
                self._log_operation("Updated feedback", feedback_id)
                return True

        except Exception as e:
            self.logger.error(f"Failed to update feedback: {e}")
            return False

    def delete_feedback(self, feedback_id: str) -> bool:
        """Delete feedback."""
        try:
            with self.connection_manager.get_session() as session:
                feedback = session.query(DocumentFeedbackModel).filter(
                    DocumentFeedbackModel.id == self._validate_uuid(feedback_id)
                ).first()

                if not feedback:
                    return False

                session.delete(feedback)
                session.commit()

                self._log_operation("Deleted feedback", feedback_id)
                return True

        except Exception as e:
            self.logger.error(f"Failed to delete feedback: {e}")
            return False
