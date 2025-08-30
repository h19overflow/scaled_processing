"""
RAG-specific Kafka producer for RAG workflow events.
Handles chunking, embedding, and ingestion events using existing data models.
"""

from typing import List
from datetime import datetime

from .base_producer import BaseKafkaProducer, create_message_key
from ..data_models.chunk import TextChunk, ValidatedEmbedding
from ..data_models.events import ChunkingCompleteEvent, EmbeddingReadyEvent, IngestionCompleteEvent


class RAGProducer(BaseKafkaProducer):
    """
    Producer for RAG workflow events.
    Publishes events for chunking, embedding, and ingestion completion.
    """
    
    def get_default_topic(self) -> str:
        """Default topic for RAG events."""
        return "chunking-complete"
    
    def send_chunking_complete(self, document_id: str, chunks: List[TextChunk]) -> bool:
        """
        Send chunking complete event.
        
        Args:
            document_id: Document identifier
            chunks: List of text chunks created
            
        Returns:
            bool: True if event sent successfully
        """
        try:
            # Create event using existing data model
            event = ChunkingCompleteEvent(
                document_id=document_id,
                chunks=chunks,
                chunk_count=len(chunks)
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
                self.logger.info(f"Chunking complete event sent: {document_id} ({len(chunks)} chunks)")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send chunking complete event: {e}")
            return False
    
    def send_embedding_ready(self, document_id: str, validated_embedding: ValidatedEmbedding) -> bool:
        """
        Send embedding ready event.
        
        Args:
            document_id: Document identifier
            validated_embedding: Validated embedding data
            
        Returns:
            bool: True if event sent successfully
        """
        try:
            # Create event using existing data model
            event = EmbeddingReadyEvent(
                document_id=document_id,
                validated_embedding=validated_embedding
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
                self.logger.info(f"Embedding ready event sent: {document_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send embedding ready event: {e}")
            return False
    
    def send_ingestion_complete(
        self, 
        document_id: str, 
        vector_count: int, 
        collection_name: str
    ) -> bool:
        """
        Send ingestion complete event.
        
        Args:
            document_id: Document identifier
            vector_count: Number of vectors stored
            collection_name: ChromaDB collection name
            
        Returns:
            bool: True if event sent successfully
        """
        try:
            # Create event using existing data model
            event = IngestionCompleteEvent(
                document_id=document_id,
                vector_count=vector_count,
                collection_name=collection_name
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
                    f"Ingestion complete event sent: {document_id} "
                    f"({vector_count} vectors in {collection_name})"
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send ingestion complete event: {e}")
            return False