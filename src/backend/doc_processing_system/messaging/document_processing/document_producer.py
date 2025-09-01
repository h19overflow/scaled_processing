"""
Document-specific Kafka producer for document ingestion events.
Handles all document-related event publishing using existing data models.
"""

from typing import Optional
from datetime import datetime

from ..base.base_producer import BaseKafkaProducer, create_message_key, validate_event_data
from ...data_models.document import ParsedDocument
from ...data_models.events import FileDetectedEvent, DocumentReceivedEvent, WorkflowInitializedEvent


class DocumentProducer(BaseKafkaProducer):
    """
    Producer for document ingestion events.
    Publishes events when documents are received and workflows are initialized.
    """
    
    def get_default_topic(self) -> str:
        """Default topic for document events."""
        return "document-available"
    
    def send_file_detected(self, file_data: dict) -> bool:
        """
        Send file detected event from file system watcher.
        
        Args:
            file_data: File detection data
            
        Returns:
            bool: True if event sent successfully
        """
        try:
            # Create event using existing data model
            event = FileDetectedEvent(**file_data)
            
            # Convert to dict for Kafka
            event_data = event.dict()
            
            # Create message key for partitioning using filename as document_id
            message_key = create_message_key(
                document_id=file_data["filename"],
                user_id="file_watcher"
            )
            
            # Publish event
            success = self.publish_event(
                topic=event.topic,
                event_data=event_data,
                key=message_key
            )
            
            if success:
                self.logger.info(f"File detected event sent: {file_data['file_path']}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send file detected event: {e}")
            return False
    
    def send_document_available(self, document_data: dict) -> bool:
        """
        Send document available event.

        Args:
            document_data: Document data dictionary
            
        Returns:
            bool: True if event sent successfully
        """
        try:
            # Extract required fields from dictionary
            document_id = document_data.get("document_id")
            user_id = document_data.get("user_id", "default")
            
            # Create message key for partitioning
            message_key = create_message_key(
                document_id=document_id,
                user_id=user_id
            )
            
            # Use the document data directly as event data
            event_data = {
                **document_data,
                "timestamp": datetime.now().isoformat(),
                "event_type": "document_available"
            }
            
            # Publish event to document-available topic
            success = self.publish_event(
                topic="document-available",
                event_data=event_data,
                key=message_key
            )
            
            if success:
                self.logger.info(f"Document available event sent: {document_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send document received event: {e}")
            return False
    
    def send_workflow_initialized(
        self, 
        document_id: str, 
        workflow_types: list, 
        status: str = "initialized"
    ) -> bool:
        """
        Send workflow initialization event.
        
        Args:
            document_id: Document identifier
            workflow_types: List of workflows to initialize (e.g., ["rag", "extraction"])
            status: Workflow initialization status
            
        Returns:
            bool: True if event sent successfully
        """
        try:
            # Create event using existing data model
            event = WorkflowInitializedEvent(
                document_id=document_id,
                workflow_types=workflow_types,
                status=status
            )
            
            # Convert to dict for Kafka
            event_data = event.dict()
            
            # Create message key
            message_key = create_message_key(document_id)
            
            # Publish event
            success = self.publish_event(
                topic=event.topic,
                event_data=event_data,
                key=message_key
            )
            
            if success:
                self.logger.info(
                    f"Workflow initialized event sent: {document_id} -> {workflow_types}"
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send workflow initialized event: {e}")
            return False
    
    def send_processing_complete(self, document_id: str, status: str = "completed") -> bool:
        """
        Send processing complete event for backward compatibility.
        
        Args:
            document_id: Document identifier
            status: Processing status
            
        Returns:
            bool: True if event sent successfully
        """
        return self.send_workflow_initialized(
            document_id=document_id,
            workflow_types=["processing"],
            status=status
        )