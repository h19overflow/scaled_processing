"""
Simple Kafka handler for document processing events.
Sends and receives messages without unnecessary abstractions.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Callable, Optional

from ..base.base_producer import BaseKafkaProducer, create_message_key
from ..base.base_consumer import BaseKafkaConsumer
from ...data_models.events import FileDetectedEvent, WorkflowInitializedEvent


class KafkaHandler(BaseKafkaProducer, BaseKafkaConsumer):
    """Handles all Kafka messaging for document processing."""
    
    def __init__(self, consumer_group: str = "document_processing_v3"):
        BaseKafkaProducer.__init__(self)
        BaseKafkaConsumer.__init__(self, consumer_group)
        self._file_handler: Optional[Callable] = None
        
        self.logger = logging.getLogger(__name__)
    
    def get_default_topic(self) -> str:
        """Default topic for publishing."""
        return "document-available"
    
    def get_subscribed_topics(self) -> list:
        """Topics to consume from."""
        return ["file-detected"]
    
    def subscribe_to_file_events(self, handler: Callable[[Dict[str, Any]], bool]):
        """Subscribe to file detected events."""
        self._file_handler = handler
    
    def process_message(self, message_data: Dict[str, Any], topic: str, key: Optional[str] = None) -> bool:
        """Process incoming Kafka messages."""
        try:
            if topic == "file-detected" and self._file_handler:
                return self._file_handler(message_data)
            else:
                self.logger.warning(f"No handler for topic: {topic}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error processing {topic} message: {e}")
            return False
    
    def send_file_detected(self, file_path: str, filename: str) -> bool:
        """Send file detected event."""
        try:
            event = FileDetectedEvent(
                file_path=file_path,
                filename=filename,
                detected_at=datetime.now()
            )
            
            key = create_message_key(document_id=filename, user_id="file_watcher")
            
            success = self.publish_event(
                topic=event.topic,
                event_data=event.dict(),
                key=key
            )
            
            if success:
                self.logger.info(f"File detected: {filename}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send file detected: {e}")
            return False
    
    def send_document_ready(self, document_id: str, file_path: str, user_id: str) -> bool:
        """Send document ready for processing event."""
        try:
            event_data = {
                "document_id": document_id,
                "status": "ready_for_processing", 
                "file_path": file_path,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "event_type": "document_available"
            }
            
            key = create_message_key(document_id, user_id)
            
            success = self.publish_event(
                topic="document-available",
                event_data=event_data,
                key=key
            )
            
            if success:
                self.logger.info(f"Document ready: {document_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send document ready: {e}")
            return False
    
    def send_workflow_ready(self, document_id: str, workflow_types: list) -> bool:
        """Send workflow initialized event."""
        try:
            event = WorkflowInitializedEvent(
                document_id=document_id,
                workflow_types=workflow_types,
                status="initialized"
            )
            
            key = create_message_key(document_id)
            
            success = self.publish_event(
                topic=event.topic,
                event_data=event.dict(),
                key=key
            )
            
            if success:
                self.logger.info(f"Workflow ready: {document_id} -> {workflow_types}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send workflow ready: {e}")
            return False
    
    def send_chunking_complete(self, chunking_result: Dict[str, Any]) -> bool:
        """Send chunking complete event."""
        try:
            document_id = chunking_result.get("document_id")
            
            event_data = {
                "document_id": document_id,
                "chunk_count": chunking_result.get("chunk_count", 0),
                "embedding_model": "nomic-ai/nomic-embed-text-v1.5",
                "chunking_strategy": "chonkie_two_stage_semantic_boundary",
                "chunking_params": chunking_result.get("chunking_params", {}),
                "timestamp": datetime.now().isoformat(),
                "event_type": "chunking_complete"
            }
            
            success = self.publish_event(
                topic="chunking-complete",
                event_data=event_data,
                key=document_id
            )
            
            if success and chunking_result.get("embedded_chunks"):
                self._send_embedding_ready(document_id, chunking_result["embedded_chunks"])
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send chunking complete: {e}")
            return False
    
    def send_storage_complete(self, storage_result: Dict[str, Any], document_id: str) -> bool:
        """Send storage complete event."""
        try:
            event_data = {
                "document_id": document_id,
                "collection_name": storage_result.get("collection_name", "rag_documents"),
                "chunks_stored": storage_result.get("chunks_stored", 0),
                "weaviate_url": storage_result.get("weaviate_url", "http://localhost:8080"),
                "storage_timestamp": datetime.now().isoformat(),
                "event_type": "ingestion_complete"
            }
            
            success = self.publish_event(
                topic="ingestion-complete",
                event_data=event_data,
                key=document_id
            )
            
            if success:
                self.logger.info(f"Storage complete: {document_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send storage complete: {e}")
            return False
    
    # HELPER FUNCTIONS
    def _send_embedding_ready(self, document_id: str, embedded_chunks: list) -> bool:
        """Send embedding ready event."""
        try:
            event_data = {
                "document_id": document_id,
                "embedded_chunks_count": len(embedded_chunks),
                "embedding_dimensions": 768,
                "embedding_model": "nomic-ai/nomic-embed-text-v1.5",
                "timestamp": datetime.now().isoformat(),
                "event_type": "embedding_ready"
            }
            
            return self.publish_event(
                topic="embedding-ready",
                event_data=event_data,
                key=document_id
            )
            
        except Exception as e:
            self.logger.error(f"Failed to send embedding ready: {e}")
            return False