"""
Document Pipeline Completed Consumer for Structured Extraction

DECISION MAP & SOLUTION SUMMARY:
================================

PROBLEM: 
- Need to listen to Kafka topic "document_pipeline_completed" 
- Transform incoming message data into PipelineState
- Trigger structured extraction flow automatically

SOLUTION DESIGN:
1. Message Structure Analysis:
   - Incoming: create_message(event_type="document_pipeline_completed", data=metadata)
   - Data contains: filename, processed_content, page_count, etc.
   - Wrapped in standardized message format with timestamp, source

2. State Mapping Strategy:
   - document_text ← data["processed_content"] (extracted text)
   - document_name ← data["filename"] (original file name)
   - document_id ← deterministic UUID from filename (consistency)
   - Other fields use defaults (status="started", user_id="system")

3. UUID Generation Decision:
   - Use uuid.uuid5(NAMESPACE_DNS, filename_stem) for deterministic IDs
   - Same filename always produces same document_id
   - Ensures database consistency and prevents duplicates

4. Error Handling Approach:
   - Comprehensive try/catch around entire message processing
   - Log original message content on failures for debugging
   - Track pipeline status and log completion results

5. Consumer Architecture:
   - Extends ConsumerHandler with topic="document_pipeline_completed"
   - 6 parallel consumers for scalability
   - Group ID "structuring_processors" for load balancing

FLOW: Kafka Message → Parse JSON → Create PipelineState → Invoke Flow → Log Results
"""

import json
import uuid
import logging
from pathlib import Path
from confluent_kafka.admin import AdminClient
from src.backend.doc_processing_system.messaging.consumer import ConsumerHandler
from src.backend.doc_processing_system.pipelines.structured_extraction.models.state import PipelineState
from src.backend.doc_processing_system.pipelines.structured_extraction.core.prefect_flow import structured_extraction_flow


class StructuringConsumer(ConsumerHandler):
    """Consumer for document pipeline completed events to trigger structured extraction."""

    def __init__(self):
        super().__init__(
            broker="localhost:9092",
            topics=["document_pipeline_completed"],
            group_id="structuring_processors",
            num_consumers=6,
        )
        self.logger = logging.getLogger(__name__)

    def handle_message(self, topic: str, key: str, value: str) -> None:
        """Handle incoming document pipeline completed message."""
        try:
            message = json.loads(value)
            
            # Extract data from the message
            data = message.get("data", {})
            event_type = message.get("event_type")
            
            self.logger.info(f"Received {event_type} event for document: {data.get('filename', 'unknown')}")
            
            # Validate processed content exists
            if not data.get('processed_content'):
                self.logger.error(f"SKIPPING - No processed content in message for {data.get('filename', 'unknown')}")
                return
                
            self.logger.info(f"Processing document with {len(data.get('processed_content', ''))} characters")
            
            # Create initial pipeline state from message data
            initial_state = self._create_pipeline_state(data)
            
            # Invoke the structured extraction flow
            self.logger.info(f"Starting structured extraction for document: {initial_state.document_name}")
            result = structured_extraction_flow(initial_state)
            
            # Log the result
            if result.status == "completed":
                self.logger.info(f"Successfully completed structured extraction for {initial_state.document_name}")
            else:
                self.logger.warning(f"Structured extraction completed with status: {result.status}")
                if result.error:
                    self.logger.error(f"Error: {result.error}")
                    
        except Exception as e:
            self.logger.error(f"Failed to process message: {e}")
            self.logger.error(f"Message content: {value}")

    def _create_pipeline_state(self, data: dict) -> PipelineState:
        """Create PipelineState from Kafka message data."""
        # Extract filename and create document_id
        filename = data.get("filename", "unknown")
        document_name = filename
        
        # Generate deterministic document_id from filename
        document_id = self._generate_document_id(filename)
        
        # Get processed content (document text)
        document_text = data.get("processed_content", "")
        
        # Create and return PipelineState
        return PipelineState(
            document_text=document_text,
            document_id=document_id,
            document_name=document_name,
            status="started",
            user_id="test_user"
        )

    def _generate_document_id(self, filename: str) -> str:
        """Generate deterministic UUID from filename."""
        if not filename:
            return str(uuid.uuid4())
        
        # Use filename stem (without extension) to generate deterministic UUID
        file_stem = Path(filename).stem
        namespace = uuid.NAMESPACE_DNS
        return str(uuid.uuid5(namespace, file_stem))


def main():
    """Main function to run the structured extraction consumer."""
    from confluent_kafka.admin import AdminClient
    document_consumer = StructuringConsumer()
    document_consumer.start()

if __name__ == "__main__":
    main()

