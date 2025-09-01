"""
Embedding Consumer - Stage 2 of RAG Pipeline

Listens to: chunking-complete
Executes: Generate embeddings from chunks
Publishes: embedding-ready
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from ..base.base_consumer import BaseKafkaConsumer
from ...pipelines.rag_processing.flows.tasks import generate_embeddings_task
from .rag_producer import RAGProducer


class EmbeddingConsumer(BaseKafkaConsumer):
    """
    Independent consumer for embedding stage of RAG pipeline.
    Scales independently from chunking and storage stages.
    """
    
    def __init__(self, group_id: str = "rag_embedding_group"):
        super().__init__(group_id)
        self.logger = logging.getLogger(__name__)
        
        # Initialize RAG producer for stage events
        self.rag_producer = RAGProducer()
        
        # Track processing to avoid duplicates
        self.processing_documents = set()
        
        self.logger.info("🔢 Embedding Consumer initialized")
        self.logger.info("📨 Listening for chunking-complete events")
    
    def get_subscribed_topics(self) -> list[str]:
        """Topics this consumer subscribes to."""
        return ["chunking-complete"]
    
    def process_message(self, message_data: dict[str, Any], topic: str, key: Optional[str] = None) -> bool:
        """Process consumed message from Kafka."""
        if topic == "chunking-complete":
            return self._handle_chunking_complete(message_data)
        else:
            self.logger.warning(f"Unknown topic: {topic}")
            return True
    
    def _handle_chunking_complete(self, message_data: Dict[str, Any]) -> bool:
        """
        Handle chunking-complete events by generating embeddings.
        
        Args:
            message_data: Chunking completion event data
            
        Returns:
            bool: True if processing succeeded
        """
        try:
            document_id = message_data.get("document_id")
            chunks_file_path = message_data.get("chunks_file_path")
            chunk_count = message_data.get("chunk_count", 0)
            
            self.logger.info(f"🔢 Starting embeddings for document: {document_id}")
            self.logger.info(f"📊 Processing {chunk_count} chunks from: {chunks_file_path}")
            
            # Validate required fields
            if not document_id or not chunks_file_path:
                self.logger.error("❌ Missing document_id or chunks_file_path")
                return True
            
            # Check for duplicate processing
            if document_id in self.processing_documents:
                self.logger.warning(f"⏳ Document already processing: {document_id}")
                return True
            
            # Track processing
            self.processing_documents.add(document_id)
            
            try:
                # Execute embeddings generation asynchronously
                self.logger.info(f"🚀 Generating embeddings: {document_id}")
                
                embeddings_result = asyncio.run(self._execute_embeddings_task(
                    chunks_file_path, document_id
                ))
                
                # Publish embedding-ready event
                self._publish_embedding_ready(document_id, embeddings_result)
                
                self.logger.info(f"✅ Embeddings completed for document: {document_id}")
                return True
                
            finally:
                self.processing_documents.discard(document_id)
                
        except Exception as e:
            self.logger.error(f"❌ Error in embedding stage: {e}")
            return False
    
    async def _execute_embeddings_task(self, chunks_file_path: str, document_id: str) -> Dict[str, Any]:
        """Execute the async embeddings generation task."""
        embeddings_result = await generate_embeddings_task(
            chunks_file_path=chunks_file_path,
            model_name="BAAI/bge-large-en-v1.5",
            batch_size=32
        )
        return embeddings_result
    
    def _publish_embedding_ready(self, document_id: str, embeddings_result: Dict[str, Any]):
        """Publish embedding-ready event to Kafka."""
        try:
            embedding_ready_data = {
                "document_id": document_id,
                "embeddings_file_path": embeddings_result["embeddings_file_path"],
                "embeddings_count": embeddings_result["embeddings_count"],
                "model_used": embeddings_result["model_used"],
                "processing_time": embeddings_result["task_processing_time"],
                "event_type": "embedding_ready"
            }
            
            self.rag_producer.send_embedding_ready(embedding_ready_data)
            self.logger.info(f"📤 Published embedding-ready for {document_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to publish embedding-ready: {e}")
            raise


# Global instance for service management
embedding_consumer = EmbeddingConsumer()


def main():
    """Main function for standalone execution."""
    import signal
    import sys
    
    def signal_handler(sig, frame):
        print("\n🛑 Shutting down Embedding Consumer...")
        embedding_consumer.stop_consuming()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🚀 Starting Embedding Consumer...")
    print("📨 Listening for chunking-complete events")
    print("Press Ctrl+C to stop")
    
    try:
        embedding_consumer.start_consuming()
    except Exception as e:
        print(f"❌ Service error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()