"""
Extraction CRUD operations.
Handles all database operations related to extraction results.
"""

from typing import List
from sqlalchemy import and_

from .base_repository import BaseRepository
from ..models import StructuredDocumentModel
from ....data_models.extraction import ExtractionResult


class ExtractionCRUD(BaseRepository):
    """CRUD operations for extraction result entities."""
    
    def create(self, result: ExtractionResult) -> str:
        """Create extraction result with upsert logic (INSERT or UPDATE).

        Args:
            result: ExtractionResult object to create

        Returns:
            str: Document ID of the created extraction result

        Raises:
            Exception: If extraction result creation fails
        """
        try:
            with self.connection_manager.get_session() as session:
                # Check if extraction already exists
                existing = session.query(StructuredDocumentModel).filter(
                    and_(
                        StructuredDocumentModel.document_id == self._validate_uuid(result.document_id),
                        StructuredDocumentModel.extraction_index == result.extraction_index
                    )
                ).first()

                if existing:
                    # Update existing record
                    existing.document_name = result.document_name
                    existing.extraction_class = result.extraction_class
                    existing.extraction_text = result.extraction_text
                    existing.attributes = result.attributes
                    existing.alignment_status = result.alignment_status
                    existing.group_index = result.group_index
                    existing.description = result.description
                    existing.char_start_pos = result.char_start_pos
                    existing.char_end_pos = result.char_end_pos

                    session.flush()
                    result_id = str(existing.document_id)

                    self._log_operation("Updated extraction result", result_id,
                                      f"document: {result.document_name}, class: {result.extraction_class}")
                else:
                    # Create new record
                    result_model = StructuredDocumentModel(
                        document_id=self._validate_uuid(result.document_id),
                        document_name=result.document_name,
                        extraction_class=result.extraction_class,
                        extraction_text=result.extraction_text,
                        attributes=result.attributes,
                        alignment_status=result.alignment_status,
                        extraction_index=result.extraction_index,
                        group_index=result.group_index,
                        description=result.description,
                        char_start_pos=result.char_start_pos,
                        char_end_pos=result.char_end_pos
                    )

                    session.add(result_model)
                    session.flush()
                    result_id = str(result_model.document_id)

                    self._log_operation("Created extraction result", result_id,
                                      f"document: {result.document_name}, class: {result.extraction_class}")

                return result_id

        except Exception as e:
            self.logger.error(f"Failed to create extraction result: {e}")
            raise
    
    def get_by_document(self, document_id: str) -> List[ExtractionResult]:
        """Get all extraction results for a document.
        
        Args:
            document_id: Document ID to get extraction results for
            
        Returns:
            List[ExtractionResult]: List of extraction results for the document
        """
        try:
            uuid_id = self._validate_uuid(document_id)
            
            with self.connection_manager.get_session() as session:
                result_models = session.query(StructuredDocumentModel).filter(
                    StructuredDocumentModel.document_id == uuid_id
                ).order_by(StructuredDocumentModel.created_at).all()
                
                results = [self._model_to_extraction_result(result) for result in result_models]
                
                self._log_operation("Retrieved extraction results by document", document_id, 
                                  f"count: {len(results)}")
                return results
        
        except Exception as e:
            self.logger.error(f"Failed to get extraction results for document {document_id}: {e}")
            raise
    
    def get_by_extraction_class(self, document_id: str, extraction_class: str) -> List[ExtractionResult]:
        """Get extraction results for a specific extraction class.
        
        Args:
            document_id: Document ID
            extraction_class: Type of extraction to filter by
            
        Returns:
            List[ExtractionResult]: List of extraction results for the class
        """
        try:
            uuid_id = self._validate_uuid(document_id)
            
            with self.connection_manager.get_session() as session:
                result_models = session.query(StructuredDocumentModel).filter(
                    and_(
                        StructuredDocumentModel.document_id == uuid_id,
                        StructuredDocumentModel.extraction_class == extraction_class
                    )
                ).order_by(StructuredDocumentModel.extraction_index).all()
                
                results = [self._model_to_extraction_result(result) for result in result_models]
                
                self._log_operation("Retrieved extraction results by class", document_id,
                                  f"class: {extraction_class}, count: {len(results)}")
                return results
        
        except Exception as e:
            self.logger.error(f"Failed to get extraction results for document {document_id}, class {extraction_class}: {e}")
            raise

    def _model_to_extraction_result(self, result_model: StructuredDocumentModel) -> ExtractionResult:
        """Convert StructuredDocumentModel to ExtractionResult.
        
        Args:
            result_model: StructuredDocumentModel instance
            
        Returns:
            ExtractionResult: Converted ExtractionResult object
        """
        return ExtractionResult(
            document_id=str(result_model.document_id),
            document_name=result_model.document_name,
            extraction_class=result_model.extraction_class,
            extraction_text=result_model.extraction_text,
            attributes=result_model.attributes or {},
            alignment_status=result_model.alignment_status,
            extraction_index=result_model.extraction_index,
            group_index=result_model.group_index,
            description=result_model.description,
            char_start_pos=result_model.char_start_pos,
            char_end_pos=result_model.char_end_pos,
            timestamp=result_model.created_at
        )
