"""
Document CRUD operations.
Handles all database operations related to documents.
"""

import hashlib
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy import desc

from .base_repository import BaseRepository
from ..models import DocumentModel
from ....data_models.document import Document, ProcessingStatus


class DocumentCRUD(BaseRepository):
    """CRUD operations for document entities."""
    
    def create(self, document: Document, raw_file_hash: str) -> str:
        """Create a new document using raw file hash for duplicate detection.
        
        Args:
            document: Document object to create
            raw_file_hash: SHA-256 hash of raw file content for duplicate detection
            
        Returns:
            str: Created document ID
            
        Raises:
            Exception: If document creation fails
            ValueError: If document with same hash already exists
        """
        try:
            # Check for existing document with same raw file hash
            existing_doc = self.get_by_hash(raw_file_hash)
            if existing_doc:
                raise ValueError(f"Document with hash {raw_file_hash} already exists: {existing_doc.id}")
            
            with self.connection_manager.get_session() as session:
                doc_model = DocumentModel(
                    filename=document.filename,
                    file_type=document.file_type,
                    upload_timestamp=document.upload_timestamp,
                    user_id=document.user_id,
                    processing_status=document.processing_status.value,
                    file_size=document.file_size,
                    page_count=document.page_count,
                    content_hash=raw_file_hash
                )
                
                session.add(doc_model)
                session.flush()  # Get the ID without committing
                document_id = str(doc_model.id)
                
                self._log_operation("Created document", document_id, f"filename: {document.filename}, hash: {raw_file_hash[:16]}...")
                return document_id
        
        except Exception as e:
            self.logger.error(f"Failed to create document: {e}")
            raise
    
    def get_by_hash(self, file_hash: str) -> Optional[Document]:
        """Get document by file hash (raw or processed content).
        
        Args:
            file_hash: SHA-256 hash of file content
            
        Returns:
            Optional[Document]: Document object if found, None otherwise
        """
        try:
            with self.connection_manager.get_session() as session:
                doc_model = session.query(DocumentModel).filter(
                    DocumentModel.content_hash == file_hash
                ).first()
                
                if not doc_model:
                    self.logger.debug(f"Document not found for hash: {file_hash[:16]}...")
                    return None
                
                return self._model_to_document(doc_model)
        
        except Exception as e:
            self.logger.error(f"Failed to get document by hash {file_hash}: {e}")
            raise
    
    def check_duplicate_by_raw_file(self, file_path: str) -> tuple[bool, Optional[str]]:
        """Check if document is duplicate by computing raw file hash.
        
        
        Args:
            file_path: Path to raw file to check
            
        Returns:
            tuple[bool, Optional[str]]: (is_duplicate, existing_document_id)
        """
        try:
            raw_hash = self.generate_file_hash(file_path)
            existing_doc = self.get_by_hash(raw_hash)
            
            if existing_doc:
                self._log_operation("Duplicate detected", existing_doc.get_id(), f"file: {file_path}, hash: {raw_hash[:16]}...")
                return True, existing_doc.get_id()
            
            return False, None
            
        except Exception as e:
            self.logger.error(f"Failed to check duplicate for file {file_path}: {e}")
            raise
    
    
    def get_by_id(self, document_id: str) -> Optional[Document]:
        """Get document by ID.
        
        Args:
            document_id: Document ID to retrieve
            
        Returns:
            Optional[Document]: Document object if found, None otherwise
        """
        try:
            uuid_id = self._validate_uuid(document_id)
            
            with self.connection_manager.get_session() as session:
                doc_model = session.query(DocumentModel).filter(
                    DocumentModel.id == uuid_id
                ).first()
                
                if not doc_model:
                    self.logger.debug(f"Document not found: {document_id}")
                    return None
                
                return self._model_to_document(doc_model)
        
        except Exception as e:
            self.logger.error(f"Failed to get document {document_id}: {e}")
            raise
    
    def update_status(self, document_id: str, status: ProcessingStatus) -> bool:
        """Update document processing status.
        
        Args:
            document_id: Document ID to update
            status: New processing status
            
        Returns:
            bool: True if update was successful
        """
        try:
            uuid_id = self._validate_uuid(document_id)
            
            with self.connection_manager.get_session() as session:
                updated_rows = session.query(DocumentModel).filter(
                    DocumentModel.id == uuid_id
                ).update({
                    'processing_status': status.value,
                    'updated_at': datetime.utcnow()
                })
                
                success = updated_rows > 0
                if success:
                    self._log_operation("Updated document status", document_id, f"status: {status.value}")
                else:
                    self.logger.warning(f"No document found to update: {document_id}")
                
                return success
        
        except Exception as e:
            self.logger.error(f"Failed to update document status {document_id}: {e}")
            raise
    
    def get_by_user(self, user_id: str, limit: int = 50) -> List[Document]:
        """Get documents by user ID.
        
        Args:
            user_id: User ID to filter by
            limit: Maximum number of documents to return
            
        Returns:
            List[Document]: List of user's documents
        """
        try:
            with self.connection_manager.get_session() as session:
                doc_models = session.query(DocumentModel).filter(
                    DocumentModel.user_id == user_id
                ).order_by(desc(DocumentModel.created_at)).limit(limit).all()
                
                documents = [self._model_to_document(doc) for doc in doc_models]
                
                self._log_operation("Retrieved documents by user", user_id, f"count: {len(documents)}")
                return documents
        
        except Exception as e:
            self.logger.error(f"Failed to get documents for user {user_id}: {e}")
            raise
    
    def get_by_status(self, status: ProcessingStatus) -> List[Document]:
        """Get documents by processing status.
        
        Args:
            status: Processing status to filter by
            
        Returns:
            List[Document]: List of documents with specified status
        """
        try:
            with self.connection_manager.get_session() as session:
                doc_models = session.query(DocumentModel).filter(
                    DocumentModel.processing_status == status.value
                ).all()
                
                documents = [self._model_to_document(doc) for doc in doc_models]
                
                self._log_operation("Retrieved documents by status", details=f"status: {status.value}, count: {len(documents)}")
                return documents
        
        except Exception as e:
            self.logger.error(f"Failed to get documents by status {status}: {e}")
            raise
    
    def delete(self, document_id: str) -> bool:
        """Delete document and all related data.
        
        Args:
            document_id: Document ID to delete
            
        Returns:
            bool: True if deletion was successful
        """
        try:
            uuid_id = self._validate_uuid(document_id)
            
            with self.connection_manager.get_session() as session:
                deleted_rows = session.query(DocumentModel).filter(
                    DocumentModel.id == uuid_id
                ).delete()
                
                success = deleted_rows > 0
                if success:
                    self._log_operation("Deleted document", document_id)
                else:
                    self.logger.warning(f"No document found to delete: {document_id}")
                
                return success
        
        except Exception as e:
            self.logger.error(f"Failed to delete document {document_id}: {e}")
            raise
    
    def update_metadata(self, document_id: str, **kwargs) -> bool:
        """Update document metadata fields.
        
        Args:
            document_id: Document ID to update
            **kwargs: Fields to update
            
        Returns:
            bool: True if update was successful
        """
        try:
            uuid_id = self._validate_uuid(document_id)
            
            # Add timestamp to updates
            kwargs['updated_at'] = datetime.utcnow()
            
            with self.connection_manager.get_session() as session:
                updated_rows = session.query(DocumentModel).filter(
                    DocumentModel.id == uuid_id
                ).update(kwargs)
                
                success = updated_rows > 0
                if success:
                    self._log_operation("Updated document metadata", document_id, f"fields: {list(kwargs.keys())}")
                
                return success
        
        except Exception as e:
            self.logger.error(f"Failed to update document metadata {document_id}: {e}")
            raise
    
    def _model_to_document(self, doc_model: DocumentModel) -> Document:
        """Convert DocumentModel to Document.
        
        Args:
            doc_model: DocumentModel instance
            
        Returns:
            Document: Converted Document object
        """
        return Document(
            id=doc_model.id,
            filename=doc_model.filename,
            file_type=doc_model.file_type,
            upload_timestamp=doc_model.upload_timestamp,
            user_id=doc_model.user_id,
            processing_status=ProcessingStatus(doc_model.processing_status),
            file_size=doc_model.file_size,
            page_count=doc_model.page_count
        )
    
    @staticmethod
    def generate_file_hash(file_path: str) -> str:
        """Generate SHA-256 hash of file content for duplicate detection.
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: SHA-256 hash of file content
            
        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If file cannot be read
        """
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files efficiently
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}")
        except IOError as e:
            raise IOError(f"Error reading file {file_path}: {e}")
    
    @staticmethod
    def generate_content_hash_from_bytes(content: bytes) -> str:
        """Generate SHA-256 hash from byte content.
        
        Args:
            content: Byte content to hash
            
        Returns:
            str: SHA-256 hash of content
        """
        return hashlib.sha256(content).hexdigest()
