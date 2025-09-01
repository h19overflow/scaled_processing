"""
Chunking Consumer - Stage 1 of RAG Pipeline

Listens to: document-available
Executes: Semantic chunking + boundary refinement + formatting  
Publishes: chunking-complete
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from ..base.base_consumer import BaseKafkaConsumer
from ...pipelines.rag_processing.flows.tasks import (
    semantic_chunking_task,
    boundary_refinement_task, 
    chunk_formatting_task
)
from .rag_producer import RAGProducer


class ChunkingConsumer(BaseKafkaConsumer):
    """
    Independent consumer for chunking stage of RAG pipeline.
    Scales independently from embedding and storage stages.
    """
    
    def __init__(self, group_id: str = "rag_chunking_group"):
        super().__init__(group_id)
        self.logger = logging.getLogger(__name__)
        
        # Set up detailed logging
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # Initialize RAG producer for stage events
        try:
            self.rag_producer = RAGProducer()
            self.logger.info("✅ RAG Producer initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize RAG Producer: {e}")
            raise
        
        # Track processing to avoid duplicates
        self.processing_documents = set()
        
        # Instance identification
        self.instance_id = "chunking_consumer"
        
        self.logger.info("🔧 Chunking Consumer initialized")
        self.logger.info("📨 Listening for document-available events")
        self.logger.info(f"🆔 Instance ID: {self.instance_id}")
        self.logger.info(f"👥 Consumer Group: {group_id}")
    
    def get_subscribed_topics(self) -> list[str]:
        """Topics this consumer subscribes to."""
        return ["document-available"]
    
    def process_message(self, message_data: dict[str, Any], topic: str, key: Optional[str] = None) -> bool:
        """Process consumed message from Kafka."""
        if topic == "document-available":
            return self._handle_document_available(message_data)
        else:
            self.logger.warning(f"Unknown topic: {topic}")
            return True
    
    def _handle_document_available(self, message_data: Dict[str, Any]) -> bool:
        """
        Handle document-available events by executing chunking pipeline.
        
        Args:
            message_data: Document availability event data
            
        Returns:
            bool: True if processing succeeded
        """
        try:
            document_id = message_data.get("document_id")
            processed_file_path = message_data.get("processed_file_path")
            
            self.logger.info(f"📄 Starting chunking for document: {document_id}")
            
            # Validate required fields
            if not document_id or not processed_file_path:
                self.logger.error("❌ Missing document_id or processed_file_path")
                return True
            
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
                # Execute chunking pipeline stages asynchronously
                self.logger.info(f"🚀 Executing chunking pipeline: {document_id}")
                
                # Run the async pipeline in event loop
                chunking_result = asyncio.run(self._execute_chunking_pipeline(
                    processed_file_path, document_id
                ))
                
                # Publish chunking-complete event
                self._publish_chunking_complete(document_id, chunking_result)
                
                self.logger.info(f"✅ Chunking completed for document: {document_id}")
                return True
                
            finally:
                self.processing_documents.discard(document_id)
                
        except Exception as e:
            self.logger.error(f"❌ Error in chunking stage: {e}")
            return False
    
    async def _execute_chunking_pipeline(self, processed_file_path: str, document_id: str) -> Dict[str, Any]:
        """Execute the async chunking pipeline stages."""
        # Stage 1: Semantic Chunking (sync task)
        stage1_result = semantic_chunking_task(
            file_path=processed_file_path,
            document_id=document_id,
            chunk_size=700,
            semantic_threshold=0.75
        )
        
        # Stage 2: Boundary Refinement (async task)
        stage2_result = await boundary_refinement_task(
            stage1_result=stage1_result,
            concurrent_agents=10,
            model_name="gemini-2.0-flash",
            boundary_context=200
        )
        
        # Stage 3: Chunk Formatting (async task)
        chunking_result = await chunk_formatting_task(
            stage2_result=stage2_result
        )
        
        return chunking_result
    
    def _publish_chunking_complete(self, document_id: str, chunking_result: Dict[str, Any]):
        """Publish chunking-complete event to Kafka."""
        try:
            chunking_complete_data = {
                "document_id": document_id,
                "chunks_file_path": chunking_result["chunks_file_path"],
                "chunk_count": chunking_result["chunk_count"],
                "processing_time": chunking_result["task_processing_time"],
                "event_type": "chunking_complete"
            }
            
            self.rag_producer.send_chunking_complete(chunking_complete_data)
            self.logger.info(f"📤 Published chunking-complete for {document_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to publish chunking-complete: {e}")
            raise


# Global instance for service management
chunking_consumer = ChunkingConsumer()


def main():
    """Main function for standalone execution."""
    import signal
    import sys
    
    def signal_handler(sig, frame):
        print("\n🛑 Shutting down Chunking Consumer...")
        chunking_consumer.stop_consuming()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🚀 Starting Chunking Consumer...")
    print("📨 Listening for document-available events")
    print("Press Ctrl+C to stop")
    
    try:
        chunking_consumer.logger.info("🏃 Starting consumer main loop...")
        chunking_consumer.start_consuming()
    except KeyboardInterrupt:
        chunking_consumer.logger.info("🛑 Chunking Consumer interrupted by user")
        sys.exit(0)
    except Exception as e:
        chunking_consumer.logger.error(f"❌ Service error: {e}")
        chunking_consumer.logger.exception("Full exception details:")
        print(f"❌ Service error: {e}")
        sys.exit(1)
    finally:
        chunking_consumer.logger.info("🔚 Chunking Consumer main() finished")


if __name__ == "__main__":
    main()