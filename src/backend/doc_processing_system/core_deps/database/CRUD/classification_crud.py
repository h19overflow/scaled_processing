"""
CRUD operations for document classifications.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from .base_repository import BaseRepository
from ..models import DocumentClassificationModel


class ClassificationCRUD(BaseRepository):
    """CRUD operations for document classifications."""

    def create_classification(
            self,
            document_id: str,
            user_id: str,
            classification: str,
            confidence_score: float,
            classification_method: str,
            keywords_found: Optional[List[str]] = None
    ) -> Optional[DocumentClassificationModel]:
        """Create new document classification."""
        try:
            with self.connection_manager.get_session() as session:
                classification_record = DocumentClassificationModel(
                    document_id=self._validate_uuid(document_id),
                    user_id=user_id,
                    classification=classification,
                    confidence_score=confidence_score,
                    classification_method=classification_method,
                    keywords_found=keywords_found or []
                )

                session.add(classification_record)
                session.commit()
                session.refresh(classification_record)

                self._log_operation("Created classification", str(classification_record.id))
                return classification_record

        except Exception as e:
            self.logger.error(f"Failed to create classification: {e}")
            return None

    def get_document_classification(
            self,
            document_id: str
    ) -> Optional[DocumentClassificationModel]:
        """Get most recent classification for document."""
        try:
            with self.connection_manager.get_session() as session:
                return session.query(DocumentClassificationModel).filter(
                    DocumentClassificationModel.document_id == self._validate_uuid(document_id)
                ).order_by(desc(DocumentClassificationModel.created_at)).first()

        except Exception as e:
            self.logger.error(f"Failed to get document classification: {e}")
            return None

    def get_classifications_by_type(
            self,
            classification: str,
            user_id: str,
            limit: int = 10
    ) -> List[DocumentClassificationModel]:
        """Get recent classifications by type for user."""
        try:
            with self.connection_manager.get_session() as session:
                return session.query(DocumentClassificationModel).filter(
                    and_(
                        DocumentClassificationModel.classification == classification,
                        DocumentClassificationModel.user_id == user_id
                    )
                ).order_by(
                    desc(DocumentClassificationModel.confidence_score),
                    desc(DocumentClassificationModel.created_at)
                ).limit(limit).all()

        except Exception as e:
            self.logger.error(f"Failed to get classifications by type: {e}")
            return []

    def update_classification(
            self,
            classification_id: str,
            classification: Optional[str] = None,
            confidence_score: Optional[float] = None,
            keywords_found: Optional[List[str]] = None
    ) -> bool:
        """Update existing classification."""
        try:
            with self.connection_manager.get_session() as session:
                record = session.query(DocumentClassificationModel).filter(
                    DocumentClassificationModel.id == self._validate_uuid(classification_id)
                ).first()

                if not record:
                    return False

                if classification is not None:
                    record.classification = classification
                if confidence_score is not None:
                    record.confidence_score = confidence_score
                if keywords_found is not None:
                    record.keywords_found = keywords_found

                session.commit()
                self._log_operation("Updated classification", classification_id)
                return True

        except Exception as e:
            self.logger.error(f"Failed to update classification: {e}")
            return False

    def delete_classification(self, classification_id: str) -> bool:
        """Delete classification."""
        try:
            with self.connection_manager.get_session() as session:
                record = session.query(DocumentClassificationModel).filter(
                    DocumentClassificationModel.id == self._validate_uuid(classification_id)
                ).first()

                if not record:
                    return False

                session.delete(record)
                session.commit()

                self._log_operation("Deleted classification", classification_id)
                return True

        except Exception as e:
            self.logger.error(f"Failed to delete classification: {e}")
            return False
