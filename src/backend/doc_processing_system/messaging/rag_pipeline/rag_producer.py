"""
RAG-specific Kafka producer for RAG workflow events.
Handles chunking, embedding, and ingestion events using existing data models.
"""

from typing import List
from datetime import datetime

from ..base.base_producer import BaseKafkaProducer, create_message_key
from ...data_models.chunk import TextChunk, ValidatedEmbedding
from ...data_models.events import ChunkingCompleteEvent, EmbeddingReadyEvent, IngestionCompleteEvent


class RAGProducer(BaseKafkaProducer):
    """
    Producer for RAG workflow events.
    Publishes events for chunking, embedding, and ingestion completion.
    """
    
    def get_default_topic(self) -> str:
        """Default topic for RAG events."""
        return "chunking-complete"
    
    def send_chunking_complete(self, event_data: dict) -> bool:
        """
        Send chunking complete event.
        
        Args:
            event_data: Dict containing chunking completion data
            
        Returns:
            bool: True if event sent successfully
        """
        try:
            document_id = event_data.get("document_id", "unknown")
            
            # Create message key
            message_key = create_message_key(document_id)
            
            # Add timestamp
            event_data["timestamp"] = datetime.now().isoformat()
            
            # Publish event
            success = self.publish_event(
                topic="chunking-complete",
                event_data=event_data,
                key=message_key
            )
            
            if success:
                chunk_count = event_data.get("chunk_count", 0)
                self.logger.info(f"Chunking complete event sent: {document_id} ({chunk_count} chunks)")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send chunking complete event: {e}")
            return False
    
    def send_embedding_ready(self, event_data: dict) -> bool:
        """
        Send embedding ready event.
        
        Args:
            event_data: Dict containing embedding completion data
            
        Returns:
            bool: True if event sent successfully
        """
        try:
            document_id = event_data.get("document_id", "unknown")
            
            # Create message key
            message_key = create_message_key(document_id)
            
            # Add timestamp
            event_data["timestamp"] = datetime.now().isoformat()
            
            # Publish event
            success = self.publish_event(
                topic="embedding-ready",
                event_data=event_data,
                key=message_key
            )
            
            if success:
                embeddings_count = event_data.get("embeddings_count", 0)
                self.logger.info(f"Embedding ready event sent: {document_id} ({embeddings_count} embeddings)")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send embedding ready event: {e}")
            return False
    
    def send_ingestion_complete(self, event_data: dict) -> bool:
        """
        Send ingestion complete event.
        
        Args:
            event_data: Dict containing ingestion completion data
            
        Returns:
            bool: True if event sent successfully
        """
        try:
            document_id = event_data.get("document_id", "unknown")
            
            # Create message key
            message_key = create_message_key(document_id)
            
            # Add timestamp
            event_data["timestamp"] = datetime.now().isoformat()
            
            # Publish event
            success = self.publish_event(
                topic="ingestion-complete",
                event_data=event_data,
                key=message_key
            )
            
            if success:
                collection_name = event_data.get("collection_name", "unknown")
                self.logger.info(f"Ingestion complete event sent: {document_id} (collection: {collection_name})")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send ingestion complete event: {e}")
            return False