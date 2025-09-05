"""
File processing consumer for handling file-detected events.
Uses Prefect flow orchestration for robust document processing pipeline.
ENHANCED ARCHITECTURE - Complete flow orchestration with retry logic and monitoring.
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from ..base.base_consumer import BaseKafkaConsumer
from ..document_processing.document_producer import DocumentProducer
from ...data_models.events import FileDetectedEvent
from ...core_deps.database import ConnectionManager, DocumentCRUD
from ...data_models.document import Document, ProcessingStatus, FileType

class FileProcessingConsumer(BaseKafkaConsumer):
    """
    Consumer for file-detected events using Prefect flow orchestration.
    Uses the enhanced document_processing_flow for complete pipeline execution.
    """

    def __init__(self, group_id: Optional[str] = None):
        """
        Initialize file processing consumer with Prefect flow orchestration.
        
        Args:
            group_id: Consumer group ID, defaults to 'file_processing_group'
        """
        super().__init__(group_id or "file_processing_group")
        self.logger = logging.getLogger(__name__)
        
        # Initialize core components directly (no wrapper layers)
        self.connection_manager = ConnectionManager()
        self.document_crud = DocumentCRUD(self.connection_manager)
        
        # Import Prefect flow for document processing
        from ...pipelines.document_processing.flows.document_processing_flow import document_processing_flow
        self.document_processing_flow = document_processing_flow
        self.document_producer = DocumentProducer()

        self.logger.info("FileProcessingConsumer initialized with Prefect flow orchestration")
    
    def get_subscribed_topics(self) -> List[str]:
        """Topics this consumer subscribes to."""
        return ["file-detected"]
    
    def process_message(self, message_data: Dict[str, Any], topic: str, key: Optional[str] = None) -> bool:
        """
        Process consumed messages based on topic.
        
        Args:
            message_data: Deserialized message data
            topic: Topic the message came from
            key: Optional message key
            
        Returns:
            bool: True if processing successful
        """
        try:
            if topic == "file-detected":
                import asyncio
                return asyncio.run(self._handle_file_detected(message_data, key))
            else:
                self.logger.warning(f"Unknown topic: {topic}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error processing message from {topic}: {e}")
            return False
    
    async def _handle_file_detected(self, message_data: Dict[str, Any], key: Optional[str]) -> bool:
        """
        Handle file detected events with direct component integration.
        SIMPLIFIED: No wrapper pipeline, direct processing flow.
        
        Args:
            message_data: Event data
            key: Message key
            
        Returns:
            bool: True if handled successfully
        """
        try:
            # Parse event using existing data model
            event = FileDetectedEvent(**message_data)
            
            self.logger.info(f"File detected: {event.filename} at {event.file_path}")
            
            # Validate file still exists (could have been moved/deleted)
            file_path = Path(event.file_path)
            if not file_path.exists():
                self.logger.warning(f"File no longer exists, skipping: {event.file_path}")
                return True  # Not an error, just skip
            
            # Validate file size matches (ensure file is completely written)
            current_size = file_path.stat().st_size
            if current_size != event.file_size:
                self.logger.warning(
                    f"File size mismatch (expected: {event.file_size}, current: {current_size}), "
                    f"file may still be writing: {event.file_path}"
                )
                # Could implement retry logic here, but for now skip
                return True
            
            # Extract user_id from file path or default
            user_id = self._extract_user_id(event.file_path)
            
            # PREFECT FLOW PROCESSING: Use orchestrated pipeline
            return await self._process_document_with_flow(file_path, user_id)
            
        except Exception as e:
            self.logger.error(f"Failed to handle file detected event: {e}")
            return False
    
    async def _process_document_with_flow(self, file_path: Path, user_id: str) -> bool:
        """
        Process document using Prefect flow orchestration.
        Uses the enhanced document_processing_flow for complete pipeline execution.

        Args:
            file_path: Path to the document
            user_id: User ID for the document

        Returns:
            bool: True if processing successful
        """
        try:
            self.logger.info(f"Starting Prefect flow processing for: {file_path}")

            # Execute the complete document processing flow
            flow_result = await self.document_processing_flow(
                raw_file_path=str(file_path),
                user_id=user_id,
                enable_weaviate_storage=False,  # Can be made configurable
                weaviate_collection="advanced_docs"
            )

            # Process flow results
            status = flow_result.get("status")

            if status == "completed":
                # Successful processing
                document_id = flow_result.get("document_id")
                self.logger.info(f"✅ Document processing flow completed: {document_id}")

                # Store document in database if not already stored by flow
                await self._ensure_document_in_database(flow_result, file_path, user_id)

                # Publish event for downstream processing
                kafka_message = flow_result.get("kafka_message")
                if kafka_message:
                    success = self.document_producer.send_document_available(kafka_message)
                    if success:
                        self.logger.info(f"📨 Document available event published: {document_id}")
                    else:
                        self.logger.error(f"❌ Failed to publish document available event: {document_id}")
                        return False
                else:
                    self.logger.warning(f"⚠️ No Kafka message in flow result: {document_id}")

                return True

            elif status == "duplicate":
                # Duplicate document - not an error
                document_id = flow_result.get("document_id")
                self.logger.info(f"📋 Document is duplicate, processing skipped: {document_id}")
                return True

            elif status == "error":
                # Processing error
                error_msg = flow_result.get("message", "Unknown error")
                self.logger.error(f"❌ Document processing flow failed: {error_msg}")
                return False

            else:
                # Unexpected status
                self.logger.error(f"❌ Unexpected flow status: {status}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Failed to execute document processing flow for {file_path}: {e}")
            return False

    async def _ensure_document_in_database(self, flow_result: Dict[str, Any], file_path: Path, user_id: str) -> None:
        """
        Ensure document is properly stored in database.
        The flow should handle this, but we double-check for consistency.

        Args:
            flow_result: Result from document processing flow
            file_path: Original file path
            user_id: User ID
        """
        try:
            document_id = flow_result.get("document_id")
            if not document_id:
                self.logger.warning("No document_id in flow result, cannot update database")
                return

            # Check if document exists in database
            existing_doc = self.document_crud.get_by_id(document_id)
            if existing_doc:
                # Update with flow results if needed
                self.document_crud.update_metadata(
                    document_id,
                    page_count=flow_result.get("page_count", 0),
                    processing_status=ProcessingStatus.COMPLETED.value
                )
                self.logger.info(f"📄 Updated existing document in database: {document_id}")
            else:
                # Create document record if somehow missing
                document = self._create_document_record(file_path, user_id)
                document.processing_status = ProcessingStatus.COMPLETED
                raw_hash = self.document_crud.generate_file_hash(str(file_path))

                created_id = self.document_crud.create(document, raw_hash)
                self.logger.info(f"📄 Created missing document record: {created_id}")

        except Exception as e:
            self.logger.error(f"❌ Failed to ensure document in database: {e}")
            # Don't fail the whole process for database sync issues
    
    def _create_document_record(self, file_path: Path, user_id: str) -> Document:
        """Create document record from file path."""
        file_stats = file_path.stat()
        
        # Determine file type
        file_type_mapping = {
            '.pdf': FileType.PDF,
            '.docx': FileType.DOCX,
            '.txt': FileType.TEXT,
            '.md': FileType.TEXT
        }
        file_type = file_type_mapping.get(file_path.suffix.lower(), FileType.TEXT)
        
        return Document(
            filename=file_path.name,
            file_type=file_type.value,
            upload_timestamp=datetime.now(),
            user_id=user_id,
            processing_status=ProcessingStatus.UPLOADED,
            file_size=file_stats.st_size,
            page_count=None
        )
    
    def _extract_user_id(self, file_path: str) -> str:
        """
        Extract user ID from file path or return default.
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: User ID
        """
        # Simple implementation - you could enhance this
        # to extract user from folder structure or filename
        return "file_watcher_user"


def create_file_processing_consumer() -> FileProcessingConsumer:
    """
    Create a file processing consumer using Prefect flow orchestration.

    Returns:
        FileProcessingConsumer: Consumer configured with enhanced flow pipeline
    """
    return FileProcessingConsumer("file_processing_group")