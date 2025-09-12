"""
Extraction CRUD operations.
Handles all database operations related to extraction results.
"""

from typing import List
from uuid import UUID
from sqlalchemy import and_

from .base_repository import BaseRepository
from ..models import StructuredDocumentModel
from ....data_models.extraction import ExtractionResult


class ExtractionCRUD(BaseRepository):
    """CRUD operations for extraction result entities."""
    
    def create(self, result: ExtractionResult) -> str:
        """Create extraction result and return its ID.
        
        Args:
            result: ExtractionResult object to create
            
        Returns:
            str: Created extraction result ID
            
        Raises:
            Exception: If extraction result creation fails
        """
        try:
            with self.connection_manager.get_session() as session:
                result_model = StructuredDocumentModel(
                    document_id=self._validate_uuid(result.document_id),
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
                result_id = str(result_model.id)
                
                self._log_operation("Created extraction result", result_id, 
                                  f"document: {result.document_id}, agent: {result.agent_id}")
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
    
    def get_by_page_range(self, document_id: str, start_page: int, end_page: int) -> List[ExtractionResult]:
        """Get extraction results for a specific page range.
        
        Args:
            document_id: Document ID
            start_page: Starting page number
            end_page: Ending page number
            
        Returns:
            List[ExtractionResult]: List of extraction results in the page range
        """
        try:
            uuid_id = self._validate_uuid(document_id)
            
            with self.connection_manager.get_session() as session:
                result_models = session.query(StructuredDocumentModel).filter(
                    StructuredDocumentModel.document_id == uuid_id
                ).all()
                
                results = [self._model_to_extraction_result(result) for result in result_models]
                
                self._log_operation("Retrieved extraction results by page range", document_id,
                                  f"pages: {start_page}-{end_page}, count: {len(results)}")
                return results
        
        except Exception as e:
            self.logger.error(f"Failed to get extraction results for document {document_id}, pages {start_page}-{end_page}: {e}")
            raise
    
    def get_by_agent(self, agent_id: str) -> List[ExtractionResult]:
        """Get extraction results by agent ID.
        
        Args:
            agent_id: Agent ID to filter by
            
        Returns:
            List[ExtractionResult]: List of extraction results from the agent
        """
        try:
            with self.connection_manager.get_session() as session:
                result_models = session.query(StructuredDocumentModel).filter(
                    StructuredDocumentModel.document_id.isnot(None)
                ).order_by(StructuredDocumentModel.created_at).all()
                
                results = [self._model_to_extraction_result(result) for result in result_models]
                
                self._log_operation("Retrieved extraction results by agent", agent_id,
                                  f"count: {len(results)}")
                return results
        
        except Exception as e:
            self.logger.error(f"Failed to get extraction results for agent {agent_id}: {e}")
            raise
    
    def update_confidence_scores(self, result_id: str, confidence_scores: dict) -> bool:
        """Update confidence scores for an extraction result.
        
        Args:
            result_id: Extraction result ID to update
            confidence_scores: New confidence scores
            
        Returns:
            bool: True if update was successful
        """
        try:
            uuid_id = self._validate_uuid(result_id)
            
            with self.connection_manager.get_session() as session:
                updated_rows = session.query(StructuredDocumentModel).filter(
                    StructuredDocumentModel.id == uuid_id
                ).update({'alignment_status': confidence_scores})
                
                success = updated_rows > 0
                if success:
                    self._log_operation("Updated extraction result confidence scores", result_id)
                
                return success
        
        except Exception as e:
            self.logger.error(f"Failed to update confidence scores for extraction result {result_id}: {e}")
            raise
    
    def delete_by_document(self, document_id: str) -> int:
        """Delete all extraction results for a document.
        
        Args:
            document_id: Document ID to delete extraction results for
            
        Returns:
            int: Number of extraction results deleted
        """
        try:
            uuid_id = self._validate_uuid(document_id)
            
            with self.connection_manager.get_session() as session:
                deleted_count = session.query(StructuredDocumentModel).filter(
                    StructuredDocumentModel.document_id == uuid_id
                ).delete()
                
                self._log_operation("Deleted extraction results by document", document_id,
                                  f"count: {deleted_count}")
                return deleted_count
        
        except Exception as e:
            self.logger.error(f"Failed to delete extraction results for document {document_id}: {e}")
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
