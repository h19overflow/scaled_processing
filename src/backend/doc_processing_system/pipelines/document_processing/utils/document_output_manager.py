"""
DocumentOutputManager - Bridge between duplicate checking, processing, saving, and message preparation.

This class orchestrates the complete document processing workflow:
1. Duplicate detection using DocumentCRUD 
2. Document processing via DoclingProcessor (if not duplicate)
3. Robust file path management for processed documents
4. Message preparation for Kafka producers (DocumentProducer)

Acts as the central coordination point for all document processing operations.
"""

import logging
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import json

from ....core_deps.database import ConnectionManager, DocumentCRUD
from ....data_models.document import Document, ProcessingStatus, FileType
from ....messaging.document_processing.kafka_handler import KafkaHandler


class DocumentOutputManager:
    """
    Central manager for document processing workflow with duplicate detection,
    robust file path management, and Kafka message preparation.
    """
    
    def __init__(self, processed_documents_dir: str = "data/documents/processed"):
        """
        Initialize the DocumentOutputManager.
        
        Args:
            processed_documents_dir: Base directory for processed documents
        """
        self.logger = logging.getLogger(__name__)
        
        # Initialize database components
        self.connection_manager = ConnectionManager()
        self.document_crud = DocumentCRUD(self.connection_manager)
        
        # Initialize messaging components
        self.kafka = KafkaHandler()
        
        # Set up directory structure
        self.processed_dir = Path(processed_documents_dir)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"DocumentOutputManager initialized with output dir: {self.processed_dir}")
    
    def check_and_process_document(self, 
                                 raw_file_path: str, 
                                 user_id: str = "default") -> Dict[str, Any]:
        """
        Complete workflow: check for duplicates, process if new, save results, prepare messages.
        
        Args:
            raw_file_path: Path to the raw document file
            user_id: User who uploaded the document
            
        Returns:
            Dict containing processing results and message data for Kafka
        """
        try:
            raw_path = Path(raw_file_path)
            
            # Step 1: Check for duplicates using content hash
            self.logger.info(f"Checking for duplicates: {raw_path.name}")
            is_duplicate, existing_doc_id = self.document_crud.check_duplicate_by_raw_file(str(raw_path))
            
            if is_duplicate:
                self.logger.info(f"Document is duplicate, skipping processing: {existing_doc_id}")
                return {
                    "status": "duplicate",
                    "document_id": existing_doc_id,
                    "message": f"Document already processed: {existing_doc_id}",
                    "processed_path": None,
                    "kafka_message": None
                }
            
            # Step 2: Generate unique document ID for new document
            document_id = self._generate_document_id(raw_path)
            self.logger.info(f"Processing new document: {document_id}")
            
            # Step 3: Save basic document record IMMEDIATELY to prevent duplicate processing
            try:
                from ....data_models.document import Document, ProcessingStatus
                file_stats = raw_path.stat()
                
                # Create basic document record
                document = Document(
                    filename=raw_path.name,
                    file_type=raw_path.suffix.lower().replace('.', ''),
                    upload_timestamp=datetime.now(),
                    user_id=user_id,
                    processing_status=ProcessingStatus.PARSING,  # Mark as being processed
                    file_size=file_stats.st_size,
                    page_count=None
                )
                
                # Generate file hash and save to database immediately
                raw_hash = self.document_crud.generate_file_hash(str(raw_path))
                db_document_id = self.document_crud.create(document, raw_hash)
                
                self.logger.info(f"Document record created in database: {db_document_id}")
                
                # Send document ready event directly
                self.kafka.send_document_ready(document_id, str(raw_path), user_id)
                
                processing_result = {
                    "status": "ready_for_processing", 
                    "document_id": document_id,
                    "db_document_id": db_document_id,
                    "raw_file_path": str(raw_path),
                    "user_id": user_id,
                    "message": f"Document ready for processing: {document_id}"
                }
                
                return processing_result
                
            except Exception as e:
                self.logger.error(f"Failed to create document record: {e}")
                # Continue with processing even if database save fails
                processing_result = {
                    "status": "ready_for_processing",
                    "document_id": document_id,
                    "raw_file_path": str(raw_path),
                    "user_id": user_id,
                    "message": f"Document ready for processing: {document_id}"
                }
                
                return processing_result
            
        except Exception as e:
            self.logger.error(f"Error in check_and_process_document: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to check/process document: {e}"
            }
    
    def save_processed_document(self, 
                               document_id: str,
                               processed_content: str,
                               metadata: Dict[str, Any],
                               user_id: str = "default") -> Dict[str, Any]:
        """
        Save processed document with vision-enhanced content and create robust file paths.
        
        Args:
            document_id: Unique document identifier
            processed_content: Vision-enhanced markdown content
            metadata: Document metadata (filename, page_count, etc.)
            user_id: User who uploaded the document
            
        Returns:
            Dict containing save results and file paths
        """
        try:
            # Step 1: Create robust directory structure
            document_dir = self._create_document_directory(document_id)
            
            # Step 2: Save processed markdown with vision enhancements
            processed_file_path = self._save_processed_markdown(
                document_dir, document_id, processed_content, metadata
            )
            
            # Step 3: Save processing metadata
            metadata_file_path = self._save_processing_metadata(
                document_dir, document_id, metadata, user_id
            )
            
            # Step 4: Store document record in database
            self._store_document_in_database(document_id, metadata, user_id)
            
            # Step 5: Send completion events directly
            self.send_processing_complete_events(document_id, str(processed_file_path), metadata, user_id)
            
            self.logger.info(f"Document saved successfully: {document_id}")
            
            return {
                "status": "saved",
                "document_id": document_id,
                "processed_file_path": str(processed_file_path),
                "metadata_file_path": str(metadata_file_path),
                "document_directory": str(document_dir),
                "message": f"Document processed and saved: {document_id}"
            }
            
        except Exception as e:
            self.logger.error(f"Error saving processed document {document_id}: {e}")
            return {
                "status": "error",
                "document_id": document_id,
                "error": str(e),
                "message": f"Failed to save document: {e}"
            }
    
    def send_processing_complete_events(self, 
                                      document_id: str, 
                                      processed_file_path: str,
                                      metadata: Dict[str, Any],
                                      user_id: str = "default") -> bool:
        """Send workflow ready event directly - no message preparation needed."""
        try:
            # Send workflow initialized event
            success = self.kafka.send_workflow_ready(document_id, ["rag", "extraction"])
            
            if success:
                self.logger.info(f"Processing complete events sent for: {document_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending processing events for {document_id}: {e}")
            return False
    
    def get_document_path_info(self, document_id: str) -> Dict[str, Any]:
        """
        Get file path information for a processed document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Dict containing all file paths for the document
        """
        try:
            document_dir = self.processed_dir / document_id
            
            if not document_dir.exists():
                return {
                    "status": "not_found",
                    "message": f"Document directory not found: {document_id}"
                }
            
            # Build path information
            path_info = {
                "status": "found",
                "document_id": document_id,
                "document_directory": str(document_dir),
                "processed_markdown": str(document_dir / f"{document_id}_processed.md"),
                "metadata_file": str(document_dir / f"{document_id}_metadata.json"),
                "exists": {
                    "directory": document_dir.exists(),
                    "markdown": (document_dir / f"{document_id}_processed.md").exists(),
                    "metadata": (document_dir / f"{document_id}_metadata.json").exists()
                }
            }
            
            return path_info
            
        except Exception as e:
            self.logger.error(f"Error getting document path info for {document_id}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to get path info: {e}"
            }
    
    # HELPER FUNCTIONS
    def _generate_document_id(self, file_path: Path) -> str:
        """Generate document ID using original filename."""
        # Use the original filename without extension as the document ID
        file_stem = file_path.stem  # filename without extension
        return file_stem
    
    def _create_document_directory(self, document_id: str) -> Path:
        """Create directory structure for document."""
        document_dir = self.processed_dir / document_id
        document_dir.mkdir(parents=True, exist_ok=True)
        return document_dir
    
    def _save_processed_markdown(self, 
                               document_dir: Path, 
                               document_id: str, 
                               content: str,
                               metadata: Dict[str, Any]) -> Path:
        """Save processed markdown with vision enhancements."""
        markdown_file = document_dir / f"{document_id}_processed.md"
        
        with open(markdown_file, 'w', encoding='utf-8') as f:
            # Header with document info
            f.write(f"# Processed Document: {metadata.get('filename', 'unknown')}\n\n")
            f.write(f"**Document ID**: {document_id}\n")
            f.write(f"**Pages**: {metadata.get('page_count', 0)}\n")
            f.write(f"**Processing Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Content Length**: {len(content):,} characters\n\n")
            f.write("---\n\n")
            
            # Vision-enhanced content
            f.write("## Document Content with AI Vision Enhancement\n\n")
            f.write(content)
        
        return markdown_file
    
    def _save_processing_metadata(self, 
                                document_dir: Path, 
                                document_id: str, 
                                metadata: Dict[str, Any],
                                user_id: str) -> Path:
        """Save processing metadata as JSON."""
        metadata_file = document_dir / f"{document_id}_metadata.json"
        
        processing_metadata = {
            "document_id": document_id,
            "user_id": user_id,
            "processing_timestamp": datetime.now().isoformat(),
            "filename": metadata.get("filename", "unknown"),
            "page_count": metadata.get("page_count", 0),
            "content_length": metadata.get("content_length", 0),
            "file_type": metadata.get("file_type", "pdf"),
            "file_size": metadata.get("file_size", 0),
            "vision_processing": metadata.get("vision_processing", True),
            "document_directory": str(document_dir),
            "processed_file": f"{document_id}_processed.md",
            "status": "completed"
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(processing_metadata, f, indent=2)
        
        return metadata_file
    
    def _store_document_in_database(self, 
                                   document_id: str, 
                                   metadata: Dict[str, Any], 
                                   user_id: str):
        """Store document record in database using DocumentCRUD."""
        try:
            # Create Document object
            document = Document(
                filename=metadata.get("filename", "unknown"),
                file_type=metadata.get("file_type", "pdf"),
                upload_timestamp=datetime.now(),
                user_id=user_id,
                processing_status=ProcessingStatus.COMPLETED,
                file_size=metadata.get("file_size", 0),
                page_count=metadata.get("page_count", 0)
            )
            
            # Generate content hash from processed content
            content = metadata.get("processed_content", "")
            content_hash = self.document_crud.generate_content_hash_from_bytes(content.encode('utf-8'))
            
            # Store in database
            db_document_id = self.document_crud.create(document, content_hash)
            self.logger.info(f"Document stored in database: {db_document_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to store document in database: {e}")
            # Don't raise - file processing can continue without DB storage