"""
File processing consumer for handling file-detected events.
Direct integration with DoclingProcessor and database operations.
SIMPLIFIED ARCHITECTURE - No wrapper layers needed.
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from ..base.base_consumer import BaseKafkaConsumer
from ...data_models.events import FileDetectedEvent
from ...core_deps.database import ConnectionManager, DocumentCRUD
from ...data_models.document import Document, ProcessingStatus, FileType
from ..document_processing.kafka_handler import KafkaHandler

class FileProcessingConsumer(BaseKafkaConsumer):
    """
    Consumer for file-detected events.
    SIMPLIFIED: Direct integration with DoclingProcessor and database operations.
    """

    def __init__(self, group_id: Optional[str] = None):
        """
        Initialize file processing consumer with direct component access.

        Args:
            group_id: Consumer group ID, defaults to 'file_processing_group'
        """
        super().__init__(group_id or "file_processing_group")
        self.logger = logging.getLogger(__name__)

        # Initialize core components directly (no wrapper layers)
        self.connection_manager = ConnectionManager()
        self.document_crud = DocumentCRUD(self.connection_manager)

        # Lazy import to avoid circular imports
        from ...pipelines.document_processing.chonkie_processor import ChonkieProcessor
        self.chonkie_processor = ChonkieProcessor()
        self.kafka = KafkaHandler()

        self.logger.info("FileProcessingConsumer initialized with direct component integration")

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

            # SIMPLIFIED PROCESSING: Direct component integration
            return await self._process_document_directly(file_path, user_id)

        except Exception as e:
            self.logger.error(f"Failed to handle file detected event: {e}")
            return False

    async def _process_document_directly(self, file_path: Path, user_id: str) -> bool:
        """
        Process document directly using core components.
        SIMPLIFIED: No wrapper pipeline needed.

        Args:
            file_path: Path to the document
            user_id: User ID for the document

        Returns:
            bool: True if processing successful
        """
        try:
            self.logger.info(f"Starting direct document processing for: {file_path}")

            # STEP 1: Early duplicate detection (CHEAP operation)
            is_duplicate, existing_doc_id = self.document_crud.check_duplicate_by_raw_file(str(file_path))

            if is_duplicate:
                self.logger.info(f"Document is duplicate, skipping processing: {file_path}")
                return True  # Duplicate is not an error

            # STEP 2: Process new document (EXPENSIVE operation - only if needed)
            self.logger.info(f"New document detected, starting processing: {file_path}")

            # Create document record
            document = self._create_document_record(file_path, user_id)
            raw_hash = self.document_crud.generate_file_hash(str(file_path))

            # Store in database with PARSING status
            document.processing_status = ProcessingStatus.PARSING
            document_id = self.document_crud.create(document, raw_hash)

            # Process with ChonkieProcessor directly (no wrapper)
            processed_result = await self.chonkie_processor.process_document_with_duplicate_check(str(file_path), user_id)

            # Update document with processing results
            self.document_crud.update_metadata(
                document_id,
                page_count=processed_result.get("page_count", 0),
                processing_status=ProcessingStatus.COMPLETED.value
            )

            # STEP 3: Send events directly for downstream processing
            self.kafka.send_document_ready(document_id, str(file_path), user_id)
            self.kafka.send_workflow_ready(document_id, ["rag", "extraction"])

            self.logger.info(f"Document processing completed: {document_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to process document {file_path}: {e}")

            # Update status to FAILED if document was created
            if 'document_id' in locals():
                try:
                    self.document_crud.update_metadata(
                        document_id,
                        processing_status=ProcessingStatus.FAILED.value
                    )
                except Exception:
                    pass  # Don't fail on cleanup errors

            return False

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

