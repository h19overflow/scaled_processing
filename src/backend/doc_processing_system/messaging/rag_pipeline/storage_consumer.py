"""
Storage Consumer - Stage 3 of RAG Pipeline

Listens to: embedding-ready
Executes: Store vectors in ChromaDB
Publishes: ingestion-complete
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from ..base.base_consumer import BaseKafkaConsumer
from ...pipelines.rag_processing.flows.tasks import store_vectors_task
from .rag_producer import RAGProducer


class StorageConsumer(BaseKafkaConsumer):
    """
    Independent consumer for storage stage of RAG pipeline.
    Scales independently from chunking and embedding stages.
    """
    
    def __init__(self, group_id: str = "rag_storage_group"):
        super().__init__(group_id)
        self.logger = logging.getLogger(__name__)
        
        # Initialize RAG producer for stage events
        self.rag_producer = RAGProducer()
        
        # Track processing to avoid duplicates
        self.processing_documents = set()
        
        self.logger.info("🗄️ Storage Consumer initialized")
        self.logger.info("📨 Listening for embedding-ready events")
    
    def get_subscribed_topics(self) -> list[str]:
        """Topics this consumer subscribes to."""
        return ["embedding-ready"]
    
    def process_message(self, message_data: dict[str, Any], topic: str, key: Optional[str] = None) -> bool:
        """Process consumed message from Kafka."""
        if topic == "embedding-ready":
            return self._handle_embedding_ready(message_data)
        else:
            self.logger.warning(f"Unknown topic: {topic}")
            return True
    
    def _handle_embedding_ready(self, message_data: Dict[str, Any]) -> bool:
        """
        Handle embedding-ready events by storing vectors in ChromaDB.
        
        Args:
            message_data: Embedding completion event data
            
        Returns:
            bool: True if processing succeeded
        """
        try:
            document_id = message_data.get("document_id")
            embeddings_file_path = message_data.get("embeddings_file_path")
            embeddings_count = message_data.get("embeddings_count", 0)
            model_used = message_data.get("model_used", "unknown")
            
            self.logger.info(f"🗄️ Starting storage for document: {document_id}")
            self.logger.info(f"📊 Storing {embeddings_count} vectors from: {embeddings_file_path}")
            self.logger.info(f"🤖 Model used: {model_used}")
            
            # Validate required fields
            if not document_id or not embeddings_file_path:
                self.logger.error("❌ Missing document_id or embeddings_file_path")
                return True
            
            # Check for duplicate processing
            if document_id in self.processing_documents:
                self.logger.warning(f"⏳ Document already processing: {document_id}")
                return True
            
            # Track processing
            self.processing_documents.add(document_id)
            
            try:
                # Execute vector storage
                self.logger.info(f"🚀 Storing vectors: {document_id}")
                
                storage_result = store_vectors_task(
                    embeddings_file_path=embeddings_file_path,
                    collection_name="rag_documents"
                )
                
                # Publish ingestion-complete event
                self._publish_ingestion_complete(document_id, storage_result)
                
                self.logger.info(f"✅ Storage completed for document: {document_id}")
                return True
                
            finally:
                self.processing_documents.discard(document_id)
                
        except Exception as e:
            self.logger.error(f"❌ Error in storage stage: {e}")
            return False
    
    def _publish_ingestion_complete(self, document_id: str, storage_result: Dict[str, Any]):
        """Publish ingestion-complete event to Kafka."""
        try:
            ingestion_complete_data = {
                "document_id": document_id,
                "collection_name": storage_result["collection_name"],
                "vectors_stored": True,
                "processing_time": storage_result["task_processing_time"],
                "event_type": "ingestion_complete"
            }
            
            self.rag_producer.send_ingestion_complete(ingestion_complete_data)
            self.logger.info(f"📤 Published ingestion-complete for {document_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to publish ingestion-complete: {e}")
            raise


# Global instance for service management
storage_consumer = StorageConsumer()


def main():
    """Main function for standalone execution."""
    import signal
    import sys
    
    def signal_handler(sig, frame):
        print("\n🛑 Shutting down Storage Consumer...")
        storage_consumer.stop_consuming()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🚀 Starting Storage Consumer...")
    print("📨 Listening for embedding-ready events")
    print("Press Ctrl+C to stop")
    
    try:
        storage_consumer.start_consuming()
    except Exception as e:
        print(f"❌ Service error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()