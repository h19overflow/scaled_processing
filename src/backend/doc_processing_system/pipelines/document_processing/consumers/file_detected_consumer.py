"""
Consumer that processes file_detected Kafka messages and triggers document processing.
"""

import asyncio
import json
from src.backend.doc_processing_system.messaging.consumer import ConsumerHandler
from src.backend.doc_processing_system.pipelines.document_processing.flows.document_processing_flow import process_document_with_flow


class FileDetectedConsumer(ConsumerHandler):
    """Consumes file_detected messages from Kafka and processes documents."""
    
    def __init__(
        self, 
        user_id: str = "default", 
        enable_vision_enhancement: bool = True,
        enable_chunking: bool = True,
        num_consumers: int = 1
    ):
        super().__init__(
            broker="localhost:9092",
            topics=["file_detected"], 
            group_id="doc_processors",
            num_consumers=num_consumers
        )
        self.user_id = user_id
        self.enable_vision_enhancement = enable_vision_enhancement
        self.enable_chunking = enable_chunking
    
    def handle_message(self, topic: str, key: str, value: str) -> None:
        """Handle Kafka message and trigger document processing."""
        message = json.loads(value)
        metadata = message["data"]
        file_path = metadata["file_path"]

        self.logger.info(f"Processing: {metadata['file_name']}")
        
        # Create new event loop for async processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                process_document_with_flow(
                    raw_file_path=file_path,
                    user_id=self.user_id,
                    enable_weaviate_storage=False,
                    weaviate_collection="rag_documents",
                    enable_vision_enhancement=self.enable_vision_enhancement,
                    enable_chunking=self.enable_chunking
                )
            )
            self.logger.info(f"Completed processing: {metadata['file_name']} - {result.get('status')}")
        finally:
            loop.close()


if __name__ == "__main__":
    consumer = FileDetectedConsumer(
        user_id="default",
        enable_vision_enhancement=False,
        enable_chunking=False,
        num_consumers=6
    )
    consumer.start()