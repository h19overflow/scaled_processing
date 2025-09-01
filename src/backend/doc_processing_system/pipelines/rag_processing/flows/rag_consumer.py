"""
RAG Processing Kafka Consumer.
Listens for document-available events and triggers RAG processing pipeline.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from ....messaging.base.base_consumer import BaseKafkaConsumer
from .rag_processing_flow import rag_processing_flow


class RagProcessingConsumer(BaseKafkaConsumer):
    """
    Consumer for document-available events to trigger RAG pipeline.
    
    Receives processed documents and executes:
    - Two-stage chunking with semantic analysis
    - Embeddings generation with validated models  
    - ChromaDB vector storage and ingestion
    """
    
    def __init__(self, group_id: str = "rag_processing_group"):
        """
        Initialize RAG processing consumer.
        
        Args:
            group_id: Kafka consumer group ID for load balancing
        """
        super().__init__(group_id)
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # Track processing documents to avoid duplicates
        self.processing_documents = set()
        
        self.logger.info("🚀 RAG Processing Consumer initialized")
        self.logger.info("📨 Listening for document-available events")
    
    def get_subscribed_topics(self) -> list[str]:
        """Topics this consumer subscribes to."""
        return ["document-available"]
    
    def process_message(self, message_data: dict[str, Any], topic: str, key: Optional[str] = None) -> bool:
        """
        Process consumed message from Kafka.
        
        Args:
            message_data: Document availability event data
            topic: Topic name
            key: Message key
            
        Returns:
            bool: True if processing successful
        """
        if topic == "document-available":
            return asyncio.run(self._handle_document_available(message_data))
        else:
            self.logger.warning(f"Unknown topic: {topic}")
            return True
    
    async def _handle_document_available(self, message_data: Dict[str, Any]) -> bool:
        """
        Handle document-available events by triggering RAG processing pipeline.
        
        Args:
            message_data: Document availability event data
            
        Returns:
            bool: True if processing succeeded
        """
        try:
            # Extract document information
            document_id = message_data.get("document_id")
            processed_file_path = message_data.get("processed_file_path")
            
            self.logger.info(f"📄 Processing document: {document_id}")
            self.logger.info(f"📁 File: {processed_file_path}")
            
            # Validate required fields
            if not document_id or not processed_file_path:
                self.logger.error("❌ Missing document_id or processed_file_path")
                return True  # Skip invalid messages
            
            # Check for duplicate processing
            if document_id in self.processing_documents:
                self.logger.warning(f"⏳ Document already processing: {document_id}")
                return True
            
            # Validate file exists
            if not Path(processed_file_path).exists():
                self.logger.warning(f"⚠️ File not found: {processed_file_path}")
                return True
            
            # Track processing
            self.processing_documents.add(document_id)
            
            try:
                # Execute RAG pipeline
                self.logger.info(f"🚀 Starting RAG pipeline: {document_id}")
                
                result = await rag_processing_flow(
                    file_path=processed_file_path,
                    document_id=document_id
                )
                
                # Log result
                status = result.get("pipeline_status")
                if status == "success":
                    self.logger.info(f"✅ RAG pipeline completed: {document_id}")
                else:
                    self.logger.error(f"❌ RAG pipeline failed: {document_id}")
                
                return True
                
            finally:
                self.processing_documents.discard(document_id)
                
        except Exception as e:
            self.logger.error(f"❌ Error handling document-available event: {e}")
            return False
    

# Global instance for easy import and standalone execution
rag_processing_consumer = RagProcessingConsumer()


def main():
    """Main function for standalone execution."""
    import signal
    import sys
    
    def signal_handler(sig, frame):
        print("\\n🛑 Shutting down RAG Processing Consumer...")
        rag_processing_consumer.stop_consuming()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🚀 Starting RAG Processing Consumer...")
    print("📨 Listening for document-available events")
    print("Press Ctrl+C to stop")
    
    try:
        rag_processing_consumer.start_consuming()
    except Exception as e:
        print(f"❌ Service error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()