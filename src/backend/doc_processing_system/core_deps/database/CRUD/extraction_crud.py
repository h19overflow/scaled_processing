"""
Extraction CRUD operations.
Handles all database operations related to extraction results.
"""

from typing import List
from uuid import UUID
from sqlalchemy import and_

from .base_repository import BaseRepository
from ..models import ExtractionResultModel
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
                result_model = ExtractionResultModel(
                    document_id=self._validate_uuid(result.document_id),
                    page_range_start=result.page_range[0],
                    page_range_end=result.page_range[1],
                    extracted_fields=result.extracted_fields,
                    confidence_scores=result.confidence_scores,
                    agent_id=result.agent_id
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
                result_models = session.query(ExtractionResultModel).filter(
                    ExtractionResultModel.document_id == uuid_id
                ).order_by(ExtractionResultModel.created_at).all()
                
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
                result_models = session.query(ExtractionResultModel).filter(
                    and_(
                        ExtractionResultModel.document_id == uuid_id,
                        ExtractionResultModel.page_range_start >= start_page,
                        ExtractionResultModel.page_range_end <= end_page
                    )
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
                result_models = session.query(ExtractionResultModel).filter(
                    ExtractionResultModel.agent_id == agent_id
                ).order_by(ExtractionResultModel.created_at).all()
                
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
                updated_rows = session.query(ExtractionResultModel).filter(
                    ExtractionResultModel.id == uuid_id
                ).update({'confidence_scores': confidence_scores})
                
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
                deleted_count = session.query(ExtractionResultModel).filter(
                    ExtractionResultModel.document_id == uuid_id
                ).delete()
                
                self._log_operation("Deleted extraction results by document", document_id,
                                  f"count: {deleted_count}")
                return deleted_count
        
        except Exception as e:
            self.logger.error(f"Failed to delete extraction results for document {document_id}: {e}")
            raise
    
    def _model_to_extraction_result(self, result_model: ExtractionResultModel) -> ExtractionResult:
        """Convert ExtractionResultModel to ExtractionResult.
        
        Args:
            result_model: ExtractionResultModel instance
            
        Returns:
            ExtractionResult: Converted ExtractionResult object
        """
        return ExtractionResult(
            document_id=str(result_model.document_id),
            page_range=(result_model.page_range_start, result_model.page_range_end),
            extracted_fields=result_model.extracted_fields or {},
            confidence_scores=result_model.confidence_scores or {},
            agent_id=result_model.agent_id,
            timestamp=result_model.created_at
        )
