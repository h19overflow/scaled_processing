"""
Optimized document processing pipeline with early duplicate detection.
Checks for duplicates BEFORE expensive processing operations.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from ...core_deps.database import ConnectionManager, DocumentCRUD
from ...data_models.document import Document, ProcessingStatus, FileType
from .docling_processor import DoclingProcessor
from ...messaging.producers_n_consumers.document_producer import DocumentProducer


class OptimizedDocumentPipeline:
    """
    Document processing pipeline with early duplicate detection.
    Flow: Raw File Hash → Duplicate Check → Process Only If New → Store → Publish Event
    """
    
    def __init__(self):
        """Initialize the optimized document processing pipeline."""
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        
        # Initialize dependencies once (cached pattern)
        self.connection_manager = ConnectionManager()
        self.document_crud = DocumentCRUD(self.connection_manager)
        self.docling_processor = DoclingProcessor()
        self.document_producer = DocumentProducer()
        
        self.logger.info("Optimized document pipeline initialized")
    
    def process_document(self, file_path: str, user_id: str = "default_user") -> Dict[str, Any]:
        """
        Process document with early duplicate detection.
        
        Args:
            file_path: Path to raw document file
            user_id: User ID processing the document
            
        Returns:
            Dict with processing results and status
        """
        file_path = Path(file_path).resolve()
        
        try:
            self.logger.info(f"Starting processing for: {file_path}")
            
            # STEP 1: Early duplicate detection (CHEAP operation)
            is_duplicate, existing_doc_id = self.document_crud.check_duplicate_by_raw_file(str(file_path))
            
            if is_duplicate:
                self.logger.info(f"Document is duplicate, skipping processing: {file_path}")
                return {
                    "status": "duplicate",
                    "document_id": existing_doc_id,
                    "message": f"Document already processed",
                    "file_path": str(file_path),
                    "processed": False
                }
            
            # STEP 2: Process new document (EXPENSIVE operation - only if needed)
            self.logger.info(f"New document detected, starting processing: {file_path}")
            
            # Create initial document record
            document = self._create_document_record(file_path, user_id)
            raw_hash = self.document_crud.generate_file_hash(str(file_path))
            
            # Store in database with PARSING status
            document.processing_status = ProcessingStatus.PARSING
            document_id = self.document_crud.create(document, raw_hash)
            
            # Process with Docling (expensive operation)
            processed_result = self.docling_processor.process_document(str(file_path))
            
            # Update document with processing results
            self.document_crud.update_metadata(
                document_id,
                page_count=processed_result.get("page_count", 0),
                processing_status=ProcessingStatus.COMPLETED.value
            )
            
            # STEP 3: Publish event for downstream processing
            self.document_producer.send_document_received({
                "document_id": document_id,
                "file_path": str(file_path),
                "processed_content": processed_result,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            })
            
            self.logger.info(f"Document processing completed: {document_id}")
            
            return {
                "status": "processed",
                "document_id": document_id,
                "message": "Document processed successfully",
                "file_path": str(file_path),
                "processed": True,
                "page_count": processed_result.get("page_count", 0)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to process document {file_path}: {e}")
            
            # Update status to FAILED if document was created
            try:
                if 'document_id' in locals():
                    self.document_crud.update_metadata(
                        document_id,
                        processing_status=ProcessingStatus.FAILED.value
                    )
            except Exception:
                pass  # Don't fail on cleanup errors
            
            return {
                "status": "error",
                "message": f"Processing failed: {str(e)}",
                "file_path": str(file_path),
                "processed": False
            }

    
    def _create_document_record(self, file_path: Path, user_id: str) -> Document:
        """Create document record from file path."""
        file_stats = file_path.stat()
        
        # Determine file type
        file_extension = file_path.suffix.lower()
        file_type_mapping = {
            '.pdf': FileType.PDF,
            '.docx': FileType.DOCX,
            '.txt': FileType.TEXT,
            '.md': FileType.TEXT
        }
        file_type = file_type_mapping.get(file_extension, FileType.TEXT)
        
        return Document(
            filename=file_path.name,
            file_type=file_type.value,
            upload_timestamp=datetime.now(),
            user_id=user_id,
            processing_status=ProcessingStatus.UPLOADED,
            file_size=file_stats.st_size,
            page_count=None  # Will be updated after processing
        )
    
    def _setup_logging(self) -> None:
        """Setup logging for the pipeline."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)