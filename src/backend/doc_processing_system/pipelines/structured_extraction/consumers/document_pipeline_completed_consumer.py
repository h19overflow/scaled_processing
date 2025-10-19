"""
Document Pipeline Completed Consumer for Structured Extraction
"""

import json
import uuid
import logging
from pathlib import Path
from src.backend.doc_processing_system.messaging.consumer import ConsumerHandler
from src.backend.doc_processing_system.messaging.producer import ProducerHandler
from src.backend.doc_processing_system.messaging.message_utils import create_message
from src.backend.doc_processing_system.pipelines.structured_extraction.models.state import (
    PipelineState,
)
from dotenv import load_dotenv

load_dotenv()


class StructuringConsumer(ConsumerHandler):
    """Consumer for document pipeline completed events to trigger structured extraction."""

    def __init__(self, broker: str = "localhost:9092"):
        super().__init__(
            broker=broker,
            topics=["document_pipeline_completed"],
            group_id="structuring_processors",
            num_consumers=6,
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(
            "🚀 StructuringConsumer initialized - waiting for messages on topic: document_pipeline_completed"
        )
        # Initialize producer for job status updates
        self.status_producer = ProducerHandler(broker=broker)

    def handle_message(self, topic: str, key: str, value: str) -> None:
        """Handle incoming document pipeline completed message."""
        try:
            self.logger.info(f"🔍 Raw message received (full): {value}")
            message = json.loads(value)

            # Extract data from the message
            data = message.get("data", {})
            event_type = message.get("event_type")
            job_id = data.get("job_id") or key  # Extract job_id for tracking

            if "processed_content" in data:
                content_len = len(data.get("processed_content", ""))
                self.logger.info(f"  - Content length: {content_len}")

            self.logger.info(
                f"Received {event_type} event for document: {data.get('filename', 'unknown')}"
            )

            # Validate processed content exists
            if not data.get("processed_content"):
                self.logger.error(
                    f"SKIPPING - No processed content in message for {data.get('filename', 'unknown')}"
                )
                if job_id:
                    self._publish_job_status(
                        job_id, "FAILED", error="No processed content in message"
                    )
                return

            self.logger.info(
                f"Processing document with {len(data.get('processed_content', ''))} characters"
            )

            # Create initial pipeline state from message data
            initial_state = self._create_pipeline_state(data)

            # Invoke the structured extraction flow
            self.logger.info(
                f"Starting structured extraction for document: {initial_state.document_name}"
            )
            result = self._run_extraction_pipeline(initial_state)

            # Log the result and publish job status
            if result.status == "completed":
                self.logger.info(
                    f"Successfully completed structured extraction for {initial_state.document_name}"
                )
                # Publish COMPLETED status with bill data if available
                if job_id:
                    # Fetch bill data from the result (if available in extractions)
                    bill_data = self._extract_bill_data(result)
                    self._publish_job_status(job_id, "COMPLETED", bill_data=bill_data)
            elif result.status == "completed_duplicate":
                self.logger.info(
                    f"Document {initial_state.document_name} already processed (duplicate)"
                )
                # Publish COMPLETED status for duplicates (successful skip)
                if job_id:
                    self._publish_job_status(job_id, "COMPLETED", error=result.error)
            else:
                self.logger.warning(
                    f"Structured extraction completed with status: {result.status}"
                )
                if result.error:
                    self.logger.error(f"Error: {result.error}")
                    if job_id:
                        self._publish_job_status(job_id, "FAILED", error=result.error)

        except Exception as e:
            self.logger.error(f"Failed to process message: {e}")
            self.logger.error(f"Message content: {value}")
            # Try to extract job_id from message and publish FAILED status
            try:
                message = json.loads(value)
                job_id = message.get("data", {}).get("job_id") or key
                if job_id:
                    self._publish_job_status(job_id, "FAILED", error=str(e))
            except:
                pass

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
            user_id="test_user",
        )

    def _run_extraction_pipeline(self, initial_state: PipelineState) -> PipelineState:
        """Run extraction pipeline without Prefect orchestration."""
        try:
            from ..tasks_core.read_markdown import read_markdown
            from ..tasks_core.config_gen import generate_config
            from ..tasks_core.database_storage import store_in_database

            self.logger.info("Starting structured extraction pipeline.")

            # Initialize settings

            # Convert Pydantic model to dict for state management
            state_dict = initial_state.model_dump()
            self.logger.info(f"Initial state: {state_dict}")

            # Step 1: Chunk the document
            self.logger.info("Step 1: Reading markdown document...")
            chunk_result = read_markdown(initial_state)

            # Update state with chunking results
            state_dict.update(chunk_result)

            # Check if chunking was successful
            if state_dict.get("status") == "error":
                self.logger.error(f"Markdown reading failed: {state_dict.get('error')}")
                return PipelineState(**state_dict)

            temp_state = PipelineState(**state_dict)
            # Mock classification results, Since the only type we are working with is invoices , there is no need to classify the document.
            updated_state = {
                "classification": "invoice",
                "classification_confidence": 0.95,
                "status": "classified",
            }
            state_dict.update(updated_state)
            self.logger.info(
                f"After classification: status={state_dict.get('status')}, classification={state_dict.get('classification')}"
            )

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
                    self.logger.info(
                        f"Pipeline completed successfully. Stored {stored_count}/{total_extractions} extractions"
                    )
                elif state_dict.get("status") == "storage_skipped":
                    # Check if it's a duplicate (which is a successful skip)
                    error_msg = state_dict.get("error", "")
                    if "already exists" in error_msg:
                        state_dict["status"] = "completed_duplicate"
                        self.logger.info(f"Document already processed: {error_msg}")
                    else:
                        state_dict["status"] = "error"
                        self.logger.warning(f"Pipeline skipped storage: {error_msg}")
                else:
                    state_dict["status"] = "error"
                    self.logger.error(
                        f"Storage failed: {state_dict.get('error', 'Unknown error')}"
                    )
            else:
                state_dict["status"] = "error"
                self.logger.error(
                    f"Config generation failed: {state_dict.get('error', 'Unknown error')}"
                )

            # Return final state
            final_state = PipelineState(**state_dict)
            self.logger.info(f"Final state: status={final_state.status}")
            return final_state

        except Exception as e:
            self.logger.error(f"Extraction pipeline failed: {e}")
            # Return a failed state
            state_dict = initial_state.model_dump()
            state_dict.update({"status": "error", "error": str(e)})
            return PipelineState(**state_dict)

    def _generate_document_id(self, filename: str) -> str:
        """Generate deterministic UUID from filename."""
        if not filename:
            return str(uuid.uuid4())

        # Use filename stem (without extension) to generate deterministic UUID
        file_stem = Path(filename).stem
        namespace = uuid.NAMESPACE_DNS
        return str(uuid.uuid5(namespace, file_stem))

    def _publish_job_status(
        self, job_id: str, status: str, error: str = None, bill_data: dict = None
    ) -> None:
        """
        Publish job status update to Kafka.

        Args:
            job_id: Job identifier
            status: Job status (PROCESSING, COMPLETED, FAILED)
            error: Optional error message
            bill_data: Optional bill data
        """
        try:
            status_data = {"job_id": job_id, "status": status}

            if error:
                status_data["error"] = error
            if bill_data:
                status_data["bill_data"] = bill_data

            message = create_message(
                "job_status_update", status_data, "structuring_consumer"
            )

            self.status_producer.produce_message(
                topic="job_status_updates", key=job_id, value=message
            )
            self.logger.info(f"Published job status update: {job_id} -> {status}")
        except Exception as e:
            self.logger.error(f"Failed to publish job status for {job_id}: {e}")

    def _extract_bill_data(self, result: PipelineState) -> dict:
        """
        Extract bill data from pipeline result for job tracking.

        Args:
            result: Pipeline state with extraction results

        Returns:
            Dictionary containing bill data if available, empty dict otherwise
        """
        try:
            # Check if extractions exist and have data
            if hasattr(result, "extractions") and result.extractions:
                # Return extractions as bill_data
                return {"extractions": result.extractions}
            return {}
        except Exception as e:
            self.logger.error(f"Failed to extract bill data: {e}")
            return {}


def main():
    """Main function to run the structured extraction consumer."""
    document_consumer = StructuringConsumer()
    document_consumer.start()


if __name__ == "__main__":
    main()
