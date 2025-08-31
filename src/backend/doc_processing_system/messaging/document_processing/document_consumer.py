"""
Document-specific Kafka consumer for document ingestion events.
Handles document-received events and triggers appropriate workflows.
"""

from typing import Dict, Any, List, Optional

from ..base.base_consumer import BaseKafkaConsumer
from ...data_models.events import DocumentReceivedEvent, WorkflowInitializedEvent


class DocumentConsumer(BaseKafkaConsumer):
    """
    Consumer for document ingestion events.
    Processes document-received events and workflow initialization events.
    """
    
    def __init__(self, group_id: Optional[str] = None):
        """
        Initialize document consumer.
        
        Args:
            group_id: Consumer group ID, defaults to 'document_consumer_group'
        """
        super().__init__(group_id or "document_consumer_group")
    
    def get_subscribed_topics(self) -> List[str]:
        """Topics this consumer subscribes to."""
        return ["document-received", "workflow-initialized"]
    
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
            if topic == "document-received":
                return self._handle_document_received(message_data, key)
            elif topic == "workflow-initialized":
                return self._handle_workflow_initialized(message_data, key)
            else:
                self.logger.warning(f"Unknown topic: {topic}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error processing message from {topic}: {e}")
            return False
    
    def _handle_document_received(self, message_data: Dict[str, Any], key: Optional[str]) -> bool:
        """
        Handle document received events.
        
        Args:
            message_data: Event data
            key: Message key
            
        Returns:
            bool: True if handled successfully
        """
        try:
            # Parse event using existing data model
            event = DocumentReceivedEvent(**message_data)
            
            self.logger.info(
                f"Received document: {event.document_id} "
                f"(file: {event.parsed_document.metadata.file_type})"
            )
            
            # Log document details for Sprint 1 verification
            document_info = {
                "document_id": event.document_id,
                "filename": event.parsed_document.metadata.document_id,
                "file_type": event.parsed_document.metadata.file_type,
                "user_id": event.parsed_document.metadata.user_id,
                "page_count": event.parsed_document.page_count,
                "timestamp": event.timestamp
            }
            
            self.logger.info(f"Document details: {document_info}")
            
            # In Sprint 1, we just log the event
            # In later sprints, this will trigger Prefect workflows
            self._trigger_processing_workflows(event)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to handle document received event: {e}")
            return False
    
    def _handle_workflow_initialized(self, message_data: Dict[str, Any], key: Optional[str]) -> bool:
        """
        Handle workflow initialization events.
        
        Args:
            message_data: Event data
            key: Message key
            
        Returns:
            bool: True if handled successfully
        """
        try:
            # Parse event using existing data model
            event = WorkflowInitializedEvent(**message_data)
            
            self.logger.info(
                f"Workflow initialized for document {event.document_id}: "
                f"{event.workflow_types} (status: {event.status})"
            )
            
            # In Sprint 1, we just log the event
            # In later sprints, this will coordinate with Prefect orchestrator
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to handle workflow initialized event: {e}")
            return False
    
    def _trigger_processing_workflows(self, event: DocumentReceivedEvent) -> bool:
        """
        Trigger processing workflows for the document.
        
        Args:
            event: Document received event
            
        Returns:
            bool: True if workflows triggered successfully
        """
        try:
            # Sprint 1: Just log that we would trigger workflows
            workflow_types = ["rag_processing", "structured_extraction"]
            
            self.logger.info(
                f"Would trigger workflows for {event.document_id}: {workflow_types}"
            )
            
            # In later sprints, this will:
            # 1. Create Prefect flow runs
            # 2. Send workflow initialization events
            # 3. Monitor workflow status
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to trigger workflows: {e}")
            return False
    
    def consume_with_callback(self, callback_func) -> None:
        """
        Consume messages and call callback function for each processed message.
        
        Args:
            callback_func: Function to call after processing each message
        """
        messages = self.consume_events()
        for message in messages:
            try:
                callback_func(message)
            except Exception as e:
                self.logger.error(f"Callback function failed: {e}")


# HELPER FUNCTIONS

def create_simple_document_consumer() -> DocumentConsumer:
    """
    Create a simple document consumer for Sprint 1 testing.
    
    Returns:
        DocumentConsumer: Configured consumer instance
    """
    return DocumentConsumer("sprint1_test_group")


def log_document_filename(message: Dict[str, Any]) -> None:
    """
    Simple callback to log document filename for Sprint 1 testing.
    
    Args:
        message: Message data from consumer
    """
    try:
        if message.get('value', {}).get('parsed_document'):
            filename = message['value']['parsed_document']['metadata']['document_id']
            print(f"📄 Document filename: {filename}")
    except Exception:
        print(f"📄 Document received: {message.get('key', 'unknown')}")