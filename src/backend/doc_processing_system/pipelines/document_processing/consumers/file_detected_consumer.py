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
        enable_vision_enhancement: bool = False,
        enable_chunking: bool = False,
        num_consumers: int = 6
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
        self.logger.info(f"🔥 RECEIVED MESSAGE: topic={topic}, key={key}")
        message = json.loads(value)
        metadata = message["data"]
        file_path = metadata["file_path"]

        self.logger.info(f"🔥 PROCESSING: {metadata['file_name']} at path: {file_path}")
        
        # Create new event loop for async processing
        self.logger.info(f"🔥 CREATING EVENT LOOP for {metadata['file_name']}")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            self.logger.info(f"🔥 STARTING FLOW EXECUTION for {metadata['file_name']}")
            result = loop.run_until_complete(
                process_document_with_flow(
                    raw_file_path=file_path,
                    user_id=self.user_id,
                    enable_weaviate_storage=False,
                    weaviate_collection="rag_documents",
                    enable_vision_enhancement=False,
                    enable_chunking=False
                )
            )
            self.logger.info(f"🔥 FLOW COMPLETED: {metadata['file_name']} - Status: {result.get('status')}")
        except Exception as e:
            self.logger.error(f"🔥 FLOW FAILED: {metadata['file_name']} - Error: {e}")
            raise
        finally:
            self.logger.info(f"🔥 CLOSING EVENT LOOP for {metadata['file_name']}")
            loop.close()


if __name__ == "__main__":
    consumer = FileDetectedConsumer(
        user_id="default",
        enable_vision_enhancement=False,
        enable_chunking=False,
        num_consumers=6
    )
    consumer.start()