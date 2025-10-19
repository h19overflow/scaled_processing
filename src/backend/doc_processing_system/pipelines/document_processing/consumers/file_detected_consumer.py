"""
Consumer that processes file_detected Kafka messages and triggers document processing.
"""

import asyncio
import json
import logging
from src.backend.doc_processing_system.messaging.consumer import ConsumerHandler
from src.backend.doc_processing_system.messaging.producer import ProducerHandler
from src.backend.doc_processing_system.messaging.message_utils import create_message
from src.backend.doc_processing_system.pipelines.document_processing.flows.document_processing_flow import (
    process_document_with_flow,
)


class FileDetectedConsumer(ConsumerHandler):
    """Consumes file_detected messages from Kafka and processes documents."""

    def __init__(
        self,
        user_id: str = "default",
        num_consumers: int = 6,
        broker: str = "localhost:9092",
    ):
        super().__init__(
            broker=broker,
            topics=["file_detected"],
            group_id="doc_processors",
            num_consumers=num_consumers,
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(
            "FileDetectedConsumer initialized - listening for messages on topic: file_detected"
        )
        self.user_id = user_id
        # Initialize producer for job status updates
        self.status_producer = ProducerHandler(broker=broker)

    def handle_message(self, topic: str, key: str, value: str) -> None:
        """Handle Kafka message and trigger document processing."""
        self.logger.info(f"🔥 RECEIVED MESSAGE: topic={topic}, key={key}")
        # load the message
        message = json.loads(value)
        print("Message received: ", message)

        metadata = message["data"]
        # extract the metadata
        file_path = metadata["file_path"]
        job_id = (
            metadata.get("job_id") or key
        )  # Use job_id from metadata or fallback to key

        self.logger.info(
            f"🔥 PROCESSING: {metadata['file_name']} at path: {file_path}, job_id: {job_id}"
        )

        # Publish PROCESSING status to job_status_updates topic
        if job_id:
            self._publish_job_status(job_id, "PROCESSING")

        # Create new event loop for async processing
        self.logger.info(f"🔥 CREATING EVENT LOOP for {metadata['file_name']}")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            self.logger.info(f"🔥 STARTING FLOW EXECUTION for {metadata['file_name']}")
            result = loop.run_until_complete(
                process_document_with_flow(
                    raw_file_path=file_path, user_id=self.user_id, job_id=job_id
                )
            )
            self.logger.info(
                f"🔥 FLOW COMPLETED: {metadata['file_name']} - Status: {result.get('status')}"
            )

            # Note: Don't publish COMPLETED here - the document_pipeline_completed consumer will do it
            # when it receives the completion event from this flow

        except Exception as e:
            self.logger.error(f"🔥 FLOW FAILED: {metadata['file_name']} - Error: {e}")
            # Publish FAILED status
            if job_id:
                self._publish_job_status(job_id, "FAILED", error=str(e))
            raise
        finally:
            self.logger.info(f"🔥 CLOSING EVENT LOOP for {metadata['file_name']}")
            loop.close()

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
                "job_status_update", status_data, "file_detected_consumer"
            )

            self.status_producer.produce_message(
                topic="job_status_updates", key=job_id, value=message
            )
            self.logger.info(f"Published job status update: {job_id} -> {status}")
        except Exception as e:
            self.logger.error(f"Failed to publish job status for {job_id}: {e}")


if __name__ == "__main__":
    consumer = FileDetectedConsumer(user_id="default", num_consumers=6)
    consumer.start()
