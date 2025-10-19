"""
Job Status Consumer

Purpose: Listens to job_status_updates topic and updates job records in PostgreSQL.
Dependencies: ConsumerHandler, ConnectionManager
Role: Bridge between Kafka event stream and database persistence for job tracking.

This consumer enables event-driven job status tracking without tight coupling
between pipeline components and the API layer.
"""

import json
import logging
from typing import Dict, Any

from .consumer import ConsumerHandler
from ..core_deps.database.connection_manager import ConnectionManager
from ..core_deps.database.CRUD.job_CRUD import JobCRUD


class JobStatusConsumer(ConsumerHandler):
    """
    Consumer for job status updates from Kafka.

    Listens to job_status_updates topic and updates PostgreSQL job records.
    Enables decoupled job tracking across distributed pipeline components.
    """

    def __init__(self, db_manager: ConnectionManager, broker: str = "localhost:9092"):
        """
        Initialize job status consumer.

        Args:
            db_manager: Database connection manager for job updates
            broker: Kafka broker address
        """
        super().__init__(
            broker=broker,
            topics=["job_status_updates"],
            group_id="job_status_processors",
            num_consumers=3,
        )
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        self.logger.info(
            "JobStatusConsumer initialized - listening for job status updates"
        )

    def handle_message(self, topic: str, key: str, value: str) -> None:
        """
        Process incoming job status update message.

        Expected message format:
        {
            "event_type": "job_status_update",
            "data": {
                "job_id": "uuid-string",
                "status": "PROCESSING|COMPLETED|FAILED",
                "error": "optional error message",
                "bill_data": {"optional": "bill data"}
            },
            "timestamp": "ISO timestamp",
            "source": "component name"
        }

        Args:
            topic: Kafka topic name
            key: Message key (job_id)
            value: JSON message payload
        """
        try:
            self.logger.info(f"Received job status update: key={key}")

            # Parse message
            message = json.loads(value)
            data = message.get("data", {})

            # Extract fields
            job_id = data.get("job_id") or key
            status = data.get("status")
            error = data.get("error")
            bill_data = data.get("bill_data")

            if not job_id or not status:
                self.logger.error(f"Missing required fields in message: {value}")
                return

            # Update job in database
            success = JobCRUD(self.db_manager).update_job_status(
                job_id=job_id, status=status, error=error, bill_data=bill_data
            )

            if success:
                self.logger.info(f"Updated job {job_id} to status {status}")
            else:
                self.logger.warning(f"Failed to update job {job_id}")

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in message: {e}")
        except Exception as e:
            self.logger.error(f"Error processing job status update: {e}")
            self.logger.error(f"Message content: {value}")


def main():
    """Main function to run the job status consumer."""
    # Initialize database manager
    db_manager = ConnectionManager()

    # Create and start consumer
    consumer = JobStatusConsumer(db_manager=db_manager)
    consumer.start()


if __name__ == "__main__":
    main()
