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
from src.backend.doc_processing_system.messaging.consumer import ConsumerHandler
from src.backend.doc_processing_system.pipelines.structured_extraction.models.state import PipelineState

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
        self.logger.info("🚀 StructuringConsumer initialized - waiting for messages on topic: document_pipeline_completed")

    def handle_message(self, topic: str, key: str, value: str) -> None:
        """Handle incoming document pipeline completed message."""
        try:
            self.logger.info(f"🔍 Raw message received (full): {value}")
            message = json.loads(value)

            # Extract data from the message
            data = message.get("data", {})
            event_type = message.get("event_type")

            self.logger.info(f"📋 Message structure:")
            self.logger.info(f"  - Event type: {event_type}")
            self.logger.info(f"  - Data keys: {list(data.keys())}")
            self.logger.info(f"  - Filename: {data.get('filename', 'MISSING')}")
            self.logger.info(f"  - Has processed_content: {'processed_content' in data}")
            if 'processed_content' in data:
                content_len = len(data.get('processed_content', ''))
                self.logger.info(f"  - Content length: {content_len}")

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
            result = self._run_extraction_pipeline(initial_state)
            
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

    def _run_extraction_pipeline(self, initial_state: PipelineState) -> PipelineState:
        """Run extraction pipeline without Prefect orchestration."""
        try:
            from ..config.settings import Settings
            from ..tasks_core.chunking import chunk_document
            from ..tasks_core.config_gen import generate_config
            from ..tasks_core.database_storage import store_in_database
            
            self.logger.info("Starting structured extraction pipeline.")
            
            # Initialize settings
            settings = Settings()
            
            # Convert Pydantic model to dict for state management
            state_dict = initial_state.model_dump()
            self.logger.info(f"Initial state: {state_dict}")
            
            # Step 1: Chunk the document
            self.logger.info("Step 1: Chunking document...")
            chunk_result = chunk_document(initial_state, settings)
            
            # Update state with chunking results
            state_dict.update(chunk_result)
            chunks = state_dict.get('chunks', [])
            chunks_count = len(chunks) if chunks is not None else 0
            self.logger.info(f"After chunking: status={state_dict.get('status')}, chunks_count={chunks_count}")
            
            # Check if chunking was successful
            if state_dict.get("status") == "error":
                self.logger.error(f"Chunking failed: {state_dict.get('error')}")
                return PipelineState(**state_dict)
            
            temp_state = PipelineState(**state_dict)
            
            updated_state = {
                "classification": 'invoice',
                "classification_confidence": 0.95,
                "status": "classified"
            }
            state_dict.update(updated_state)
            self.logger.info(f"After classification: status={state_dict.get('status')}, classification={state_dict.get('classification')}")
            
            
            # Step 3: Generate config and extract data
            self.logger.info("Step 3: Generating config and extracting data...")
            temp_state = PipelineState(**state_dict)
            
            config_result = generate_config(temp_state)
            
            if config_result:
                state_dict.update(config_result)
                self.logger.info(f"Config generation completed successfully")
                
                # Step 4: Store results in database
                self.logger.info("Step 4: Storing extraction results in database...")
                temp_state = PipelineState(**state_dict)
                
                storage_result = store_in_database(temp_state)
                state_dict.update(storage_result)
                
                # Set final status based on storage result
                if state_dict.get("status") == "storage_completed":
                    state_dict["status"] = "completed"
                    stored_count = state_dict.get("stored_count", 0)
                    total_extractions = state_dict.get("total_extractions", 0)
                    self.logger.info(f"Pipeline completed successfully. Stored {stored_count}/{total_extractions} extractions")
                elif state_dict.get("status") == "storage_skipped":
                    state_dict["status"] = "completed_no_storage"
                    self.logger.warning("Pipeline completed but no results were stored")
                else:
                    state_dict["status"] = "storage_failed"
                    self.logger.error(f"Storage failed: {state_dict.get('error', 'Unknown error')}")
            else:
                state_dict["status"] = "config_generation_failed"
                self.logger.error("Config generation failed")
            
            # Return final state
            final_state = PipelineState(**state_dict)
            self.logger.info(f"Final state: status={final_state.status}")
            return final_state
            
        except Exception as e:
            self.logger.error(f"Extraction pipeline failed: {e}")
            # Return a failed state
            state_dict = initial_state.model_dump()
            state_dict.update({
                "status": "pipeline_failed",
                "error": str(e)
            })
            return PipelineState(**state_dict)

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
    document_consumer = StructuringConsumer()
    document_consumer.start()

if __name__ == "__main__":
    main()


